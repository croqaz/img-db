from .img import *
from .vhash import *

from os.path import split, splitext
from argparse import Namespace
from hashlib import blake2b
from pathlib import Path
from PIL import Image

from typing import Dict, List, Any, Union

HASH_DIGEST_SIZE = 24
VISUAL_HASH_BASE = 36


def find_files(folders: List[Path], opts: Namespace):
    to_proc = []
    index = 1
    for pth in folders:
        if not pth.is_dir():
            print(f'Path "{pth}" is not a folder!')
            continue
        for p in sorted(pth.glob('**/*.*')):
            if opts.exts:
                if p.suffix.lower() not in opts.exts:
                    continue
            to_proc.append(p)
            if opts.limit and opts.limit > 0:
                index += 1
                if index > opts.limit:
                    print(f'To process: {len(to_proc)} files')
                    return to_proc
    print(f'To process: {len(to_proc)} files')
    return to_proc


def img_meta(pth: Union[str, Path], opts: Namespace):
    try:
        img = Image.open(pth)
    except Exception as err:
        print(f"Cannot open image '{pth}'! ERROR: {err}")
        return None, {}

    bin_text = open(pth, 'rb').read()
    img_hash = blake2b(bin_text, digest_size=HASH_DIGEST_SIZE).hexdigest()

    meta = {
        'p': str(pth),
        'format': img.format,
        'mode': img.mode,
        'size': list(img.size),
        'ahash': array_to_string(ahash(img), VISUAL_HASH_BASE),
        'phash': array_to_string(phash(img), VISUAL_HASH_BASE),
        'dhash': array_to_string(diff_hash(img), VISUAL_HASH_BASE),
        'blake2s': img_hash,
        'date': get_img_date(img),
        'make-model': get_make_model(img),
        'dominant-colors': get_dominant_color(img),
    }
    if not opts.operation:
        print('META:', meta)
    return img, meta


def img_archive(meta: Dict[str, Any], opts: Namespace):
    if not meta:
        return False

    if opts.operation:
        old_name_ext = split(meta['p'])[1]
        old_name, ext = splitext(old_name_ext)
        naming = opts.naming.lower()
        if naming in ('dhash', 'blake2s'):
            new_name = meta[naming] + ext.lower()
            if new_name == old_name:
                return

            op_name = opts.operation.__name__.rstrip('2')
            print(f'{op_name}: {old_name_ext}  ->  {new_name}')
            out_dir = (opts.move or opts.copy).rstrip('/')
            opts.operation(meta['p'], f'{out_dir}/{new_name}')
            return True

    return False
