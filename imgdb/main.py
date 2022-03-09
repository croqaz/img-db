from .img import get_img_date, get_make_model
from .db import img_to_html, db_gc, db_query
from .vhash import VHASHES, array_to_string

import re
import os
from os.path import split, splitext, getsize
from argparse import Namespace
from random import shuffle
from pathlib import Path
from PIL import Image
import hashlib

from typing import Dict, List, Any, Union

HASH_DIGEST_SIZE = 24
VISUAL_HASH_BASE = 36


def main(opts: Namespace):
    stream = None
    if opts.db and opts.query:
        db_query(opts)
        return
    if opts.db:
        print(f'Using DB file "{opts.db}"')
        # open with append + read
        stream = open(opts.db + '~', 'a+')
    for f in find_files(opts.folders, opts):
        img, m = img_meta(f, opts)
        if not (img and m):
            continue
        if opts.operation:
            img_archive(m, opts)
        if stream:
            stream.write(img_to_html(img, m, opts))
    if stream:
        # consolidate DB
        stream.seek(0)
        t = db_gc(
            open(opts.db, 'r').read(),
            stream.read(),
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
            print(f'Path "{pth}" is not a folder!')
            continue
        imgs = sorted(pth.glob('**/*.*'))
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

    if opts.shuffle:
        shuffle(to_proc)
    print(f'To process: {len(to_proc)} files; found: {found} files;')
    return to_proc


def img_meta(pth: Union[str, Path], opts: Namespace):
    try:
        img = Image.open(pth)
    except Exception as err:
        print(f"Cannot open image '{pth}'! ERROR: {err}")
        return None, {}

    if opts.ignore_sz:
        w, h = img.size
        if w < opts.ignore_sz or h < opts.ignore_sz:
            print('Img too small:', img.size)
            return img, {}

    meta = {
        'pth': str(pth),
        'format': img.format,
        'mode': img.mode,
        'size': img.size,
        'bytes': getsize(pth),
        'date': get_img_date(img),
        'make-model': get_make_model(img),
        # 'dominant-colors': get_dominant_color(img),
    }

    for algo in opts.v_hashes:
        arr = VHASHES[algo](img)
        meta[algo] = array_to_string(arr, VISUAL_HASH_BASE)

    bin_text = open(pth, 'rb').read()
    for algo in opts.hashes:
        meta[algo] = hashlib.new(algo, bin_text, digest_size=HASH_DIGEST_SIZE).hexdigest()  # type: ignore

    # calculate img UID
    meta['id'] = opts.uid.format(**meta)

    if not opts.operation:
        print('META:', meta)

    return img, meta


def img_archive(meta: Dict[str, Any], opts: Namespace):
    if not meta:
        return False

    if opts.operation:
        old_name_ext = split(meta['pth'])[1]
        old_name, ext = splitext(old_name_ext)
        new_name = meta['id'] + ext.lower()
        if new_name == old_name:
            return

        op_name = opts.operation.__name__.rstrip('2')
        print(f'{op_name}: {old_name_ext}  ->  {new_name}')
        out_dir = (opts.move or opts.copy).rstrip('/')
        opts.operation(meta['pth'], f'{out_dir}/{new_name}')
        # update new location
        meta['pth'] = f'{out_dir}/{new_name}'
        return True

    return False
