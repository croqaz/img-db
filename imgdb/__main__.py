import os
import re
import fire
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from os.path import isfile
from pathlib import Path
from random import shuffle
from time import monotonic
from tqdm import tqdm
from typing import List

from .config import Config, EXTRA_META
from .db import db_open, db_save, db_debug, db_filter, db_merge
from .gallery import generate_gallery
from .img import img_to_meta, meta_to_html, img_archive
from .link import generate_links
from .log import log
from .vhash import VHASHES


def add(
    *args,
    op: str = 'copy',
    uid: str = '{blake2b}',
    archive: str = '',
    o: str = '',  # output=alias for archive
    hashes='blake2b',
    v_hashes='dhash',
    metadata='',
    filter='',
    exts: str = '',
    limit: int = 0,
    ignore_sz: int = 96,
    thumb_sz: int = 64,
    thumb_qual: int = 70,
    thumb_type: str = 'webp',
    dbname: str = 'imgdb.htm',
    workers: int = 4,
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
    archive = archive or o
    if not (archive or dbname):
        raise ValueError('No ARCHIVE or DB provided, nothing to do')
    if (op and not archive and not dbname):
        raise ValueError(f'No ARCHIVE provided for {op}, nothing to do')
    archpth = Path(archive).expanduser()
    if not archpth.is_dir():
        raise ValueError('Invalid archive path!')

    c = Config(
        inputs=[Path(f).expanduser() for f in args],
        archive=archpth,
        add_operation=op,
        uid=uid,
        hashes=hashes,
        v_hashes=v_hashes,
        metadata=metadata,
        dbname=dbname,
        filtr=filter,
        limit=limit,
        ignore_sz=ignore_sz,
        thumb_sz=thumb_sz,
        thumb_qual=thumb_qual,
        thumb_type=thumb_type,
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
    if v_hashes == '*':
        c.v_hashes = sorted(VHASHES)
    if metadata == '*':
        c.metadata = sorted(EXTRA_META)
    # setting the global state shouldn't be needed
    import imgdb.config
    imgdb.config.g_config = c

    stream = None
    if dbname:
        log.debug(f'Using DB file "{dbname}"')
        if not isfile(dbname):
            with open(dbname, 'w') as fd:
                fd.write('<!DOCTYPE html>')
        # open with append + read
        stream = open(dbname + '~', 'a+')

    def _add_img(f):
        img, m = img_to_meta(f, c)
        if not (img and m):
            return
        if archive and c.add_func:
            img_archive(m, c)
        else:
            log.debug(f'in DB: {m["pth"]}')
        return m

    files = find_files(c.inputs, c)
    with ThreadPoolExecutor(max_workers=workers) as executor, \
         tqdm(total=len(files), unit='img', dynamic_ncols=True) as progress:
        for m in executor.map(_add_img, files):
            progress.update()
            if not m:
                continue
            if stream:
                stream.write(meta_to_html(m, c))

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
    uid: str = '{blake2b}',
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
        op='move',
        uid=uid,
        archive=archive,
        hashes=hashes,
        v_hashes=v_hashes,
        metadata=metadata,
        exts=exts,
        limit=limit,
        ignore_sz=0,
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


def find_files(folders: List[Path], c):
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
    filter='',
    exts='',
    limit: int = 0,
    wrap_at: int = 1000,
    dbname: str = 'imgdb.htm',
    verbose: bool = False,
):
    """ Create gallery from DB """
    c = Config(
        gallery=name,
        dbname=dbname,
        filtr=filter,
        exts=exts,
        limit=limit,
        wrap_at=wrap_at,
        verbose=verbose,
    )
    db = db_open(dbname)
    generate_gallery(db, c)


def links(
    name: str,
    filter='',
    exts='',
    limit: int = 0,
    dbname: str = 'imgdb.htm',
    verbose: bool = False,
):
    """ Create links from archive """
    c = Config(links=name, dbname=dbname, filtr=filter, exts=exts, limit=limit, verbose=verbose)
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
    import imgdb.config
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
            head = set()
            for m in metas:
                head = head.union(m.keys())
            if not head:
                return
            head.remove('id')
            head.remove('pth')
            head = ['id', 'pth'] + sorted(head)
            print('<table style="font-family:mono">')
            print('<tr>' + ''.join(f'<td>{h}</td>' for h in head))
            for m in metas:
                print('<tr>' + ''.join(f'<td>{m.get(h,"")}</td>' for h in head) + '</tr>')
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
    }, name='imgDB')
    t1 = monotonic()
    log.info(f'img-DB finished in {t1-t0:.3f} sec')
