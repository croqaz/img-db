import os
import sys
import csv
import fire
import json
import shutil
import inspect
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
from os.path import isfile, expanduser
from pathlib import Path
from random import shuffle
from time import monotonic
from tqdm import tqdm
from typing import List, Callable
from yaml import load as yaml_load
try:
    from yaml import CLoader as Loader  # type: ignore
except ImportError:
    from yaml import Loader  # type: ignore

from .config import Config, load_config_args, IMG_DATE_FMT
from .db import db_open, db_save, db_debug, db_filter, db_merge
from .gallery import generate_gallery
from .img import img_to_meta, meta_to_html, img_archive, img_rename
from .link import generate_links
from .log import log
from .vhash import VHASHES
import imgdb.config


def create_args_for(func: Callable, loc_vars: dict):
    """ This ugly function creates config options for a command, using the config JSON and the user provided flags.
    Steps:
    - use inspect to get all default args of the command
    - calculate args that will overwrite the default config
    - calculate user args that will overwrite default args
    - optionally load the user provided config
    """
    default_args = {
        k: v.default
        for k, v in inspect.signature(func).parameters.items() if v.default is not inspect.Parameter.empty
    }
    c = Config()
    cli_args = {k: v for k, v in loc_vars.items() if k[0] != '_' and (k in default_args or k in dir(c))}
    cfg_overw = {k: v for k, v in cli_args.items() if k in dir(c) and default_args[k] != getattr(c, k)}
    user_args = {k: v for k, v in cli_args.items() if v != default_args[k] and k in dir(c)}
    config_args = load_config_args(cli_args.pop('config', ''))
    return {**cfg_overw, **config_args, **user_args}


def add(  # NOQA: C901
    *args,
    operation: str = 'copy',
    # uid: str = '{blake2b}', # this is dangerous; disabled for now
    archive: str = '',
    output: str = '',  # output=alias for archive
    o: str = '',  # output=alias for archive
    config: str = '',
    hashes='blake2b',
    v_hashes='dhash',
    metadata='',
    filter='',
    exts: str = '',
    limit: int = 0,
    thumb_sz: int = 96,
    thumb_qual: int = 70,
    thumb_type: str = 'webp',
    dbname: str = 'imgdb.htm',
    data_from: str = '',
    workers: int = 4,
    skip_imported: bool = False,
    deep: bool = False,  # deep search of imgs
    force: bool = False,  # use the force
    shuffle: bool = False,  # randomize before import
    silent: bool = False,  # only show error logs
    verbose: bool = False,  # show debug logs
):
    """ Add (import) images.
    """
    if not len(args):
        raise ValueError('Must provide at least an INPUT folder to import from')
    archive = archive or output or o
    if not (archive or dbname):
        raise ValueError('No ARCHIVE or DB provided, nothing to do')
    if (operation and not archive and not dbname):
        raise ValueError(f'No ARCHIVE provided for {operation}, nothing to do')
    archpth = Path(archive).expanduser()
    if not archpth.is_dir():
        raise ValueError('Invalid archive path!')

    j = create_args_for(add, locals())
    j['archive'] = archpth
    j['inputs'] = [Path(f).expanduser() for f in args]
    c = Config(**j)
    if operation == 'move':
        c.add_func = shutil.move
    elif operation == 'copy':
        c.add_func = shutil.copy2
    elif operation == 'link':
        c.add_func = os.link
    elif operation:
        raise ValueError('Invalid add operation!')
    if v_hashes == '*':
        c.v_hashes = sorted(VHASHES)
    # setting the global state shouldn't be needed
    imgdb.config.g_config = c

    stream = None
    if dbname:
        dbname = c.dbname
        log.debug(f'Using DB file "{dbname}"')
        if not isfile(dbname):
            with open(dbname, 'w') as fd:
                fd.write('<!DOCTYPE html>')
        # open with append + read
        stream = open(dbname + '~', 'a+')

    existing = set(el['id'] for el in db_open(dbname).find_all('img'))
    files = find_files(c.inputs, c)

    custom_data = {}
    if data_from:
        if data_from.endswith('.json'):
            custom_data = json.load(open(data_from))
        elif data_from.endswith('.yaml') or data_from.endswith('.yml'):
            custom_data = yaml_load(open(data_from), Loader=Loader)
        else:
            raise ValueError('Invalid custom-data type! Only JSON and YAML are supported!')
        # match 'image' or 'photo' or 'path' from the list objects
        custom_getter = lambda o: o.get('image') or o.get('photo') or o.get('path')
        if isinstance(custom_data, (list, tuple)):
            dict_data = {custom_getter(o): o for o in custom_data if custom_getter(o)}
            for obj in custom_data:
                if obj.get('images'):
                    for i in obj['images']:
                        dict_data.setdefault(i, {}).update(obj)
                elif obj.get('photos'):
                    for i in obj['photos']:
                        dict_data.setdefault(i, {}).update(obj)
            custom_data = dict_data

    def _add_img(p: Path):
        img, m = img_to_meta(p, c)
        if not (img and m):
            return
        if c.skip_imported and m['id'] in existing:
            log.debug(f'skip imported {m["pth"]}')
            return
        if custom_data:
            if m['pth'] in custom_data:
                m.update(custom_data[m['pth']])
            elif p.name in custom_data:
                m.update(custom_data[p.name])
        if archive and c.add_func:
            img_archive(m, c)
        elif m['id'] in existing:
            log.debug(f'update DB: {m["pth"]}')
        else:
            log.debug(f'to DB: {m["pth"]}')
        return m

    with ThreadPoolExecutor(max_workers=workers) as executor, \
         tqdm(total=len(files), unit='img', dynamic_ncols=True) as progress:
        promises = [executor.submit(_add_img, f) for f in files]
        try:
            for future in as_completed(promises):
                progress.update()
                m = future.result()
                if not m:
                    continue
                if stream:
                    stream.write(meta_to_html(m, c))
        except KeyboardInterrupt:
            for future in promises:
                future.cancel()
            for thread in executor._threads:
                thread.join(timeout=0.1)
            executor.shutdown(wait=False, cancel_futures=True)
            progress.close()
            if stream:
                stream.close()
            log.info('EXITING')
            # kill PID sigterm
            os.kill(os.getpid(), 15)
        except Exception as err:
            log.error(f'Import error: {err}')
            return

    if stream:
        # consolidate DB!
        stream.seek(0)
        stream_txt = stream.read()
        stream.close()
        if stream_txt:
            # the stream must be the second arg,
            # so it will overwrite the existing DB
            t = db_merge(
                open(dbname, 'r').read(),
                stream_txt,
            )
            db_save(t, dbname)
        os.remove(stream.name)
        # force write everything
        os.sync()


def readd(
    archive: str,
    # uid: str = '{blake2b}', # option disabled for now
    config: str = '',
    hashes='blake2b',
    v_hashes='dhash',
    metadata='',
    exts: str = '',
    limit: int = 0,
    thumb_sz: int = 64,
    thumb_qual: int = 70,
    thumb_type: str = 'webp',
    dbname: str = 'imgdb.htm',
    workers: int = 4,
    shuffle: bool = False,
    silent: bool = False,
    verbose: bool = False,
):
    """ This is a IRREVERSIBLE rename operation, be CAREFUL!
    Be extra careful if changing the default UID flag, because you CAN OVERWRITE and LOSE your images!
    This will rename and move all the images from the archive folder,
    back into the archive folder, but with different names depending on the hash and UID.
    This is useful to normalize your DB, if you want all your images to have the same thumb size,
    same hashes, same visual hashes, same metadata.
    Also useful if the already imported images don't have enough props, maybe you want to calculate
    all the visual-hashes for all the images.
    It's also possible that some images from the archive don't have the same hash anymore,
    because they were edited: eg by updating some XMP properties like rating stars, category or description.
    """
    add(
        archive,
        config=config,
        operation='move',
        archive=archive,
        hashes=hashes,
        v_hashes=v_hashes,
        metadata=metadata,
        exts=exts,
        limit=limit,
        thumb_sz=thumb_sz,
        thumb_qual=thumb_qual,
        thumb_type=thumb_type,
        dbname=dbname,
        workers=workers,
        deep=True,
        force=True,
        shuffle=shuffle,
        silent=silent,
        verbose=verbose,
    )


def rename(
    *args: str,
    output: str = '',
    o: str = '',  # output=alias for output
    name: str = '',  # the base name used to rename all imgs
    exts: str = '',
    limit: int = 0,
    hashes='blake2b',
    v_hashes='dhash',
    metadata='',
    deep: bool = False,  # deep search of imgs
    force: bool = False,  # use the force
    shuffle: bool = False,  # randomize before import
    silent: bool = False,  # only show error logs
    verbose: bool = False,  # show debug logs
):
    """ Rename (and move) matching images into output folder.
    """
    if not len(args):
        raise ValueError('Must provide at least an INPUT folder')
    if not (output or o):
        raise ValueError('Must provide an OUTPUT folder')
    if not name:
        raise ValueError('Must specify a naming pattern')
    if not isinstance(name, str):
        raise ValueError('The naming pattern MUST be a string')
    out_path = Path(output or o).expanduser()
    c = Config(
        uid=name,
        inputs=[Path(f).expanduser() for f in args],
        archive=out_path,
        hashes=hashes,
        v_hashes=v_hashes,
        metadata=metadata,
        exts=exts,  # type: ignore
        limit=limit,
        deep=deep,
        force=force,
        shuffle=shuffle,
        silent=silent,
        verbose=verbose,
    )
    if v_hashes == '*':
        c.v_hashes = sorted(VHASHES)
    for fname in tqdm(find_files(c.inputs, c), unit='img', dynamic_ncols=True):
        img, m = img_to_meta(fname, c)
        if not (img and m):
            continue
        # it's useful to have more native objects available
        m['Pth'] = Path(m['pth'])
        if m['date']:
            m['Date'] = datetime.strptime(m['date'], IMG_DATE_FMT)
        else:
            m['Date'] = datetime(1900, 1, 1, 0, 0, 0)
        img_rename(fname, m['id'], out_path, c)


def find_files(folders: List[Path], c) -> list:
    found = 0
    stop = False
    to_proc = []

    for pth in folders:
        if stop:
            break
        if not pth.is_dir():
            log.warn(f'Path "{pth}" is not a folder!')
            continue
        if c.deep:
            imgs = sorted(pth.glob('**/*.*'))
        else:
            imgs = sorted(pth.glob('*.*'))
        if c.shuffle:
            shuffle(imgs)
        found += len(imgs)
        for p in imgs:
            if c.exts and p.suffix.lower() not in c.exts:
                continue
            to_proc.append(p)
            if c.limit and c.limit > 0 and len(to_proc) >= c.limit:
                stop = True
                break

    log.info(f'Found: {found:,} files, to process: {len(to_proc):,} files')
    return to_proc


def gallery(
    name: str,
    config: str = '',
    filter='',
    exts='',
    limit: int = 0,
    tmpl: str = 'img_gallery.html',
    add_attrs: str = '',
    del_attrs: str = '',
    wrap_at: int = 1000,
    dbname: str = 'imgdb.htm',
    silent: bool = False,
    verbose: bool = False,
):
    """ Create gallery from DB """
    j = create_args_for(gallery, locals())
    j['gallery'] = expanduser(name)
    c = Config(**j)
    db = db_open(c.dbname)
    generate_gallery(db, c)


def links(
    name: str,
    config: str = '',
    filter='',
    exts='',
    limit: int = 0,
    sym_links: bool = False,
    dbname: str = 'imgdb.htm',
    force: bool = False,
    silent: bool = False,
    verbose: bool = False,
):
    """ Create links from archive """
    j = create_args_for(links, locals())
    j['links'] = expanduser(name)
    c = Config(**j)
    db = db_open(c.dbname)
    generate_links(db, c)


def db(
    op: str,
    output: str = '',
    dbname: str = 'imgdb.htm',
    filter='',
    f='',  # alias for filter
    exts='',
    limit: int = 0,
    archive: str = '',
    format: str = 'jl',
    silent: bool = False,
    verbose: bool = False,
):
    """ DB operations """
    out_path = Path(output).expanduser()
    c = Config(
        output=out_path,
        dbname=dbname,
        archive=Path(archive) if archive else None,  # type: ignore
        filter=filter or f,
        exts=exts,
        limit=limit,
        silent=silent,
        verbose=verbose,
    )
    # setting the global state shouldn't be needed
    imgdb.config.g_config = c

    db = db_open(c.dbname)
    if op == 'debug':
        db_debug(db, c)
    elif op == 'export':
        metas, _ = db_filter(db, c)
        if format == 'json':
            print(json.dumps(metas, ensure_ascii=False, indent=2))
        elif format == 'jl':
            for m in metas:
                print(json.dumps(m))
        elif format in ('csv', 'html', 'table'):
            h = set(['id'])
            for m in metas:
                h = h.union(m.keys())
            if not h:
                return
            h.remove('id')  # remove them here to have them first, in order
            h.remove('pth')
            header = ['id', 'pth'] + sorted(h)
            del h

            if output:
                fd = open(output, 'w', newline='')
            else:
                fd = sys.__stdout__

            if format == 'csv':
                writer = csv.writer(fd, quoting=csv.QUOTE_NONNUMERIC)
                writer.writerow(header)
                for m in metas:
                    writer.writerow([m.get(h, "") for h in header])
            else:
                fd.write('<table style="font-family:mono">\n')
                fd.write('<tr>' + ''.join(f'<td>{h}</td>' for h in header) + '</tr>\n')
                for m in metas:
                    fd.write('<tr>' + ''.join(f'<td>{m.get(h,"")}</td>' for h in header) + '</tr>\n')
                fd.write('</table>\n')
        else:
            raise ValueError('Invalid export format!')
    else:
        raise ValueError(f'Invalid DB op: {op}')


def main():
    t0 = monotonic()
    fire.Fire({
        'add': add,
        'db': db,
        'gallery': gallery,
        'links': links,
        'readd': readd,
        'rename': rename,
    }, name='imgDB')
    t1 = monotonic()
    log.info(f'img-DB finished in {t1-t0:.3f} sec')


if __name__ == '__main__':
    main()
