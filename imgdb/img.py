from .util import html_escape
from .vhash import VHASHES, array_to_string

from PIL import Image
from PIL.ExifTags import TAGS
from argparse import Namespace
from datetime import datetime
from os.path import split, splitext, getsize
from pathlib import Path
from typing import Dict, Any, Union
import hashlib

HASH_DIGEST_SIZE = 24
VISUAL_HASH_BASE = 36

HUMAN_TAGS = {v: k for k, v in TAGS.items()}

IMG_ATTRS = ['format', 'mode', 'width', 'height', 'bytes', 'date', 'make-model']


def get_attr_type(attr):
    if attr in ('width', 'height', 'bytes'):
        return int
    return str


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
        arr = VHASHES[algo](img)  # type: ignore
        meta[algo] = array_to_string(arr, VISUAL_HASH_BASE)

    bin_text = open(pth, 'rb').read()
    for algo in opts.hashes:
        meta[algo] = hashlib.new(algo, bin_text,
                                 digest_size=HASH_DIGEST_SIZE).hexdigest()  # type: ignore

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


def get_img_date(img: Image.Image, fmt='%Y-%m-%d %H:%M:%S'):
    # extract and format
    exif = img._getexif()  # type: ignore
    if not exif:
        return
    exif_fmt = '%Y:%m:%d %H:%M:%S'
    # (36867, 37521) # (DateTimeOriginal, SubsecTimeOriginal)
    # (36868, 37522) # (DateTimeDigitized, SubsecTimeDigitized)
    # (306, 37520)   # (DateTime, SubsecTime)
    tags = [
        HUMAN_TAGS['DateTimeOriginal'],   # when img was taken
        HUMAN_TAGS['DateTimeDigitized'],  # when img was stored digitally
        HUMAN_TAGS['DateTime'],           # when img file was changed
    ]
    for tag in tags:
        if exif.get(tag):
            dt = datetime.strptime(exif[tag], exif_fmt)
            return dt.strftime(fmt)


def get_make_model(img: Image.Image, fmt='{make}-{model}'):
    exif = img._getexif()  # type: ignore
    if not exif:
        return
    make = exif.get(HUMAN_TAGS['Make'], '').strip().replace(' ', '-').title()
    model = exif.get(HUMAN_TAGS['Model'], '').strip().replace(' ', '-')
    if make or model:
        return html_escape(fmt.format(make=make, model=model))


def get_dominant_color(img: Image.Image, sz=164, c1=16, c2=2):
    from .util import rgb_to_hex
    # TBH I'm not happy with this function
    img = img.copy()
    img.thumbnail((sz, sz))
    img = img.convert('P', palette=Image.ADAPTIVE, colors=c1).convert('RGB')
    img = img.resize((c2, c2), resample=0)
    return [rgb_to_hex(c) for _, c in sorted(img.getcolors(), key=lambda t: t[0])]
