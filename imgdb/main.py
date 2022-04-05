from .config import g_config
from .db import img_to_html, db_gc, db_query
from .gallery import generate_gallery
from .img import img_meta, img_archive
from .link import generate_links
from .log import log

import re
import os
from bs4 import BeautifulSoup
from pathlib import Path
from random import shuffle
from typing import List


def main(c=g_config):
    stream = None
    if c.db:
        log.debug(f'Using DB file "{c.db}"')
        if not c.db.is_file():
            with open(c.db, 'w') as fd:
                fd.write('<!DOCTYPE html>')
        db = BeautifulSoup(open(c.db), 'lxml')
        if c.query:
            return db_query(db, c)
        if c.links:
            return generate_links(db, c)
        if c.gallery:
            return generate_gallery(db, c)
        # open with append + read
        stream = open(c.db + '~', 'a+')

    for f in find_files(c.folders, c):
        img, m = img_meta(f, c)
        if not (img and m):
            continue
        if c.operation:
            img_archive(m, c)
        if stream:
            stream.write(img_to_html(m, c))

    if stream:
        # consolidate DB
        stream.seek(0)
        stream_txt = stream.read()
        if stream_txt:
            # the stream must be the second arg,
            # so it will overwrite the existing DB
            t = db_gc(
                open(c.db, 'r').read(),
                stream_txt,
            )
            open(c.db, 'w').write(t)
        stream.close()
        os.remove(stream.name)
        # force write everything
        os.sync()


def find_files(folders: List[Path], c=g_config):
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
