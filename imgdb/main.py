from .img import *
from .dhash import dhash_img

from os.path import split, splitext
from argparse import Namespace
from hashlib import blake2b
from pathlib import Path
from PIL import Image

from typing import Dict, List, Any, Union

HASH_DIGEST_SIZE = 24


def find_files(folders: List[Path], opts):
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


def img_meta(pth: Union[str, Path]) -> Dict[str, Any]:
    try:
        img = Image.open(pth)
    except Exception as err:
        print(f"Cannot open image '{pth}'! ERROR: {err}")
        return {}

    bin_text = open(pth, 'rb').read()
    img_hash = blake2b(bin_text, digest_size=HASH_DIGEST_SIZE).hexdigest()

    meta = {
        'p': str(pth),
        'format': img.format,
        'mode': img.mode,
        'size': list(img.size),
        'dhash': dhash_img(img),
        'blake2s': img_hash,
        'date': get_img_date(img),
        'make-model': get_make_model(img),
        'dominant-colors': get_dominant_color(img),
    }
    # save_img_meta_as_html(img, meta)
    return meta


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
