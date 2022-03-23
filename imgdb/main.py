from .db import img_to_html, db_gc, db_query
from .gallery import generate_gallery
from .img import img_meta, img_archive
from .link import generate_links
from .log import log

import re
import os
from argparse import Namespace
from bs4 import BeautifulSoup
from pathlib import Path
from random import shuffle
from typing import List


def main(opts: Namespace):
    stream = None
    if opts.db:
        log.debug(f'Using DB file "{opts.db}"')
        db = BeautifulSoup(open(opts.db), 'lxml')
        if opts.query:
            return db_query(db, opts)
        if opts.links:
            return generate_links(db, opts)
        if opts.gallery:
            return generate_gallery(db, opts)
        # open with append + read
        stream = open(opts.db + '~', 'a+')
    for f in find_files(opts.folders, opts):
        img, m = img_meta(f, opts)
        if not (img and m):
            continue
        if opts.operation:
            img_archive(m, opts.operation, (opts.move or opts.copy or ''))
        if stream:
            stream.write(img_to_html(m, opts))
    if stream:
        # consolidate DB
        stream.seek(0)
        stream_txt = stream.read()
        if stream_txt:
            # the stream must be the second arg,
            # so it will overwrite the existing DB
            t = db_gc(
                open(opts.db, 'r').read(),
                stream_txt,
            )
            open(opts.db, 'w').write(t)
        stream.close()
        os.remove(stream.name)
        # force write everything
        os.sync()


def find_files(folders: List[Path], opts: Namespace):
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
        if opts.shuffle:
            shuffle(imgs)
        found += len(imgs)
        for p in imgs:
            if opts.exts and p.suffix.lower() not in opts.exts:
                continue
            if opts.filter and not re.search(opts.filter, str(p.parent / p.name)):
                continue
            to_proc.append(p)
            if opts.limit and opts.limit > 0 and len(to_proc) >= opts.limit:
                stop = True
                break

    log.info(f'To process: {len(to_proc)} files; found: {found} files;')
    return to_proc
