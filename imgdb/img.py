from os.path import split, splitext
from argparse import Namespace
from hashlib import blake2b
from pathlib import Path
from PIL import Image

from typing import Dict, Any, Union

from .dhash import dhash_img

HASH_DIGEST_SIZE = 24


def img_meta(pth: Union[str, Path]) -> Dict[str, Any]:
    try:
        img = Image.open(pth)
    except Exception as err:
        print(f"Cannot open image '{pth}'! ERROR: {err}")
        return {}

    bin_text = open(pth, 'rb').read()
    img_hash = blake2b(bin_text, digest_size=HASH_DIGEST_SIZE).hexdigest()

    return {
        'p': str(pth),
        'size': img.size,
        'mode': img.mode,
        'format': img.format,
        'dhash': dhash_img(img),
        'blake2s': img_hash,
    }


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
