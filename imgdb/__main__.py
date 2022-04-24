import os
import re
import fire
import json
import shutil
from attrs import evolve
from concurrent.futures import as_completed, ThreadPoolExecutor
from datetime import datetime
from os.path import isfile, expanduser
from pathlib import Path
from random import shuffle
from time import monotonic
from tqdm import tqdm
from typing import List

from .config import Config, config_from_json, IMG_DATE_FMT
from .db import db_open, db_save, db_debug, db_filter, db_merge
from .gallery import generate_gallery
from .img import img_to_meta, meta_to_html, img_archive, img_rename
from .link import generate_links
from .log import log
from .vhash import VHASHES
import imgdb.config


def add(  # NOQA: C901
    *args,
    op: str = 'copy',
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
    thumb_sz: int = 64,
    thumb_qual: int = 70,
    thumb_type: str = 'webp',
    dbname: str = 'imgdb.htm',
    workers: int = 4,
    skip_imported: bool = False,
    deep: bool = False,  # deep search of imgs
    force: bool = False,  # use the force
    shuffle: bool = False,  # randomize before import
    silent: bool = False,  # only show error logs
    verbose: bool = False,  # show debug logs
):
    """ Add (import) images.
    Be extra careful if changing the default UID flag, if you use MOVE, because you CAN OVERWRITE and LOSE your images!
    """
    if not len(args):
        raise ValueError('Must provide at least an INPUT folder to import from')
    archive = archive or output or o
    if not (archive or dbname):
        raise ValueError('No ARCHIVE or DB provided, nothing to do')
    if (op and not archive and not dbname):
        raise ValueError(f'No ARCHIVE provided for {op}, nothing to do')
    archpth = Path(archive).expanduser()
    if not archpth.is_dir():
        raise ValueError('Invalid archive path!')

    c = evolve(
        config_from_json(config),
        inputs=[Path(f).expanduser() for f in args],
        archive=archpth,
        add_operation=op,
        hashes=hashes,
        v_hashes=v_hashes,
        metadata=metadata,
        dbname=dbname,
        filtr=filter,
        limit=limit,
        thumb_sz=thumb_sz,
        thumb_qual=thumb_qual,
        thumb_type=thumb_type,
        skip_imported=skip_imported,
        deep=deep,
        force=force,
        shuffle=shuffle,
        silent=silent,
        verbose=verbose,
    )
    if exts:
        c.exts = [f'.{e.lstrip(".").lower()}' for e in re.split('[,; ]', exts) if e]
    if op == 'move':
        c.add_func = shutil.move
    elif op == 'copy':
        c.add_func = shutil.copy2
    elif op == 'link':
        c.add_func = os.link
    else:
        raise ValueError('Invalid add operation!')
    if v_hashes == '*':
        c.v_hashes = sorted(VHASHES)
    # setting the global state shouldn't be needed
    imgdb.config.g_config = c

    stream = None
    if dbname:
        log.debug(f'Using DB file "{dbname}"')
        if not isfile(dbname):
            with open(dbname, 'w') as fd:
                fd.write('<!DOCTYPE html>')
        # open with append + read
        stream = open(dbname + '~', 'a+')

    existing = set(el['id'] for el in db_open(dbname).find_all('img'))
    files = find_files(c.inputs, c)

    def _add_img(f):
        img, m = img_to_meta(f, c)
        if not (img and m):
            return
        if c.skip_imported and m['id'] in existing:
            log.debug(f'skip imported {m["pth"]}')
            return
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
        op='move',
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
        limit=limit,
        deep=deep,
        force=force,
        shuffle=shuffle,
        silent=silent,
        verbose=verbose,
    )
    if exts:
        c.exts = [f'.{e.lstrip(".").lower()}' for e in re.split('[,; ]', exts) if e]
    if v_hashes == '*':
        c.v_hashes = sorted(VHASHES)
    # setting the global state shouldn't be needed
    imgdb.config.g_config = c

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

    log.info(f'To process: {len(to_proc):,} files; found: {found:,} files;')
    return to_proc


def gallery(
    name: str,
    config: str = '',
    filter='',
    exts='',
    limit: int = 0,
    wrap_at: int = 1000,
    dbname: str = 'imgdb.htm',
    silent: bool = False,
    verbose: bool = False,
):
    """ Create gallery from DB """
    c = evolve(
        config_from_json(config),
        gallery=expanduser(name),
        dbname=dbname,
        filtr=filter,
        exts=exts,
        limit=limit,
        wrap_at=wrap_at,
        silent=silent,
        verbose=verbose,
    )
    db = db_open(dbname)
    generate_gallery(db, c)


def links(
    name: str,
    config: str = '',
    filter='',
    exts='',
    limit: int = 0,
    sym_links: bool = False,
    dbname: str = 'imgdb.htm',
    silent: bool = False,
    verbose: bool = False,
):
    """ Create links from archive """
    c = evolve(
        config_from_json(config),
        links=expanduser(name),
        sym_links=sym_links,
        dbname=dbname,
        filtr=filter,
        exts=exts,
        limit=limit,
        silent=silent,
        verbose=verbose,
    )
    db = db_open(dbname)
    generate_links(db, c)


def db(
    op: str,
    filter='',
    f='',  # alias for filter
    exts='',
    limit: int = 0,
    dbname: str = 'imgdb.htm',
    archive: str = '',
    format: str = 'jl',
    silent: bool = False,
    verbose: bool = False,
):
    """ DB operations """
    c = Config(
        dbname=dbname,
        archive=Path(archive) if archive else None,  # type: ignore
        filtr=filter or f,
        exts=exts,
        limit=limit,
        silent=silent,
        verbose=verbose,
    )
    # setting the global state shouldn't be needed
    imgdb.config.g_config = c

    db = db_open(dbname)
    if op == 'debug':
        db_debug(db, c)
    elif op == 'export':
        metas, _ = db_filter(db, c)
        if format == 'json':
            print(json.dumps(metas, ensure_ascii=False, indent=2))
        elif format == 'jl':
            for m in metas:
                print(json.dumps(m))
        elif format == 'table':
            head = set(['id'])
            for m in metas:
                head = head.union(m.keys())
            if not head:
                return
            head.remove('id')  # remove them here to have them first, in order
            head.remove('pth')
            table = ['id', 'pth'] + sorted(head)
            print('<table style="font-family:mono">')
            print('<tr>' + ''.join(f'<td>{h}</td>' for h in table))
            for m in metas:
                print('<tr>' + ''.join(f'<td>{m.get(h,"")}</td>' for h in table) + '</tr>')
            print('</table>')
        else:
            raise ValueError('Invalid export format!')
    else:
        raise ValueError(f'Invalid DB op: {op}')


if __name__ == '__main__':
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
