import os
import re
import fire
import json
import shutil
from os.path import isfile
from pathlib import Path
from random import shuffle
from time import monotonic
from typing import List

import imgdb.config
from .config import Config
from .db import db_open, db_query, db_filter, db_merge
from .gallery import generate_gallery
from .img import img_to_meta, img_to_html, img_archive
from .link import generate_links
from .log import log
from .vhash import VHASHES


def add(
    *args,
    op: str = 'copy',
    uid: str = '{blake2b}',
    output: str = '',
    hashes='blake2b',
    v_hashes='dhash',
    metadata='',
    exts: str = '',
    pmatch: str = '',
    limit: int = 0,
    ignore_sz: int = 96,
    thumb_sz: int = 64,
    thumb_qual: int = 70,
    thumb_type: str = 'webp',
    dbname: str = '',
    force: bool = False,
    shuffle: bool = False,
    silent: bool = False,
    verbose: bool = False,
):
    """ Add (import) images. """
    if not len(args):
        raise ValueError('Must provide at least an INPUT folder to import from')
    if not (output or dbname):
        raise ValueError('No OUTPUT or DB provided, nothing to do')

    c = Config(
        inputs=[Path(f) for f in args],
        output=Path(output),
        add_operation=op,
        uid=uid,
        hashes=hashes,
        v_hashes=v_hashes,
        metadata=metadata,
        dbname=dbname,
        pmatch=pmatch,
        limit=limit,
        ignore_sz=ignore_sz,
        thumb_sz=thumb_sz,
        thumb_qual=thumb_qual,
        thumb_type=thumb_type,
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
    imgdb.config.g_config = c

    stream = None
    if dbname:
        log.debug(f'Using DB file "{dbname}"')
        if not isfile(dbname):
            with open(dbname, 'w') as fd:
                fd.write('<!DOCTYPE html>')
        # open with append + read
        stream = open(dbname + '~', 'a+')

    for f in find_files(c.inputs, c):
        img, m = img_to_meta(f, c)
        if not (img and m):
            continue
        if output and c.add_func:
            img_archive(m, c)
        if stream:
            stream.write(img_to_html(m, c))

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
            open(dbname, 'w').write(t)
        os.remove(stream.name)
        # force write everything
        os.sync()


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
        imgs = sorted(pth.glob('**/*.*'))
        if c.shuffle:
            shuffle(imgs)
        found += len(imgs)
        for p in imgs:
            if c.exts and p.suffix.lower() not in c.exts:
                continue
            if c.pmatch and not re.search(c.pmatch, str(p.parent / p.name)):
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
    dbname: str = 'imgdb.htm',
    verbose: bool = False,
):
    """ Create gallery from DB """
    c = Config(gallery=name, dbname=dbname, filtr=filter, exts=exts, limit=limit, verbose=verbose)
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
    exts='',
    limit: int = 0,
    dbname: str = 'imgdb.htm',
    format: str = 'jl',
    silent: bool = False,
    verbose: bool = False,
):
    """ DB operations """
    c = Config(
        dbname=dbname,
        filtr=filter,
        exts=exts,
        limit=limit,
        silent=silent,
        verbose=verbose,
    )
    db = db_open(dbname)
    if op == 'debug':
        db_query(db, c)
    elif op == 'export':
        metas, _ = db_filter(db, c)
        if format == 'json':
            print(json.dumps(metas, ensure_ascii=False, indent=2))
        elif format == 'jl':
            for m in metas:
                print(json.dumps(m))
    else:
        raise ValueError(f'Invalid DB op: {op}')


if __name__ == '__main__':
    t0 = monotonic()
    fire.Fire({
        'add': add,
        'db': db,
        'gallery': gallery,
        'links': links,
    }, name='imgDB')
    t1 = monotonic()
    log.info(f'img-DB finished in {t1-t0:.3f} sec')
