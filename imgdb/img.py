from .log import log
from .util import html_escape
from .vhash import VHASHES, array_to_string

from PIL import Image
from PIL.ExifTags import TAGS
from argparse import Namespace
from bs4 import BeautifulSoup
from bs4.element import Tag
from datetime import datetime
from os import mkdir
from os.path import split, splitext, getsize, isfile, isdir
from pathlib import Path
from typing import Dict, Callable, Any, Union
import hashlib

HASH_DIGEST_SIZE = 24
VISUAL_HASH_BASE = 36
IMG_DATE_FMT = '%Y-%m-%d %H:%M:%S'
IMG_ATTRS = ['pth', 'format', 'mode', 'width', 'height', 'bytes', 'date', 'make-model']

HUMAN_TAGS = {v: k for k, v in TAGS.items()}


def get_attr_type(attr):
    """ Common helper to get the type of a prop/attr """
    if attr in ('width', 'height', 'bytes'):
        return int
    return str


def img_meta(pth: Union[str, Path], opts: Namespace):
    """ Extract meta-data from a disk image. """
    try:
        img = Image.open(pth)
    except Exception as err:
        log.error(f"Cannot open image '{pth}'! ERROR: {err}")
        return None, {}

    if opts.ignore_sz:
        w, h = img.size
        if w < opts.ignore_sz or h < opts.ignore_sz:
            log.debug(f"Img '{pth}' too small: {img.size}")
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
    return img, meta


def el_meta(el: Tag, to_native=True):
    """
    Extract meta-data from a IMG element, from imd-db.htm.
    Full file name: pth.name
    File extension: pth.suffix
    The base name (without extension) is always the ID.
    """
    pth = el.attrs['data-pth']
    meta = {
        'pth': Path(pth) if to_native else pth,
        'id': el.attrs['id'],
        'format': el.attrs.get('data-format', ''),
        'mode': el.attrs.get('data-mode', ''),
        'bytes': int(el.attrs.get('data-bytes', 0)),
        'make-model': el.attrs.get('data-make-model', ''),
    }
    for algo in VHASHES:
        if el.attrs.get(f'data-{algo}'):
            meta[algo] = el.attrs[f'data-{algo}']
    if el.attrs.get('data-size'):
        width, height = el.attrs['data-size'].split(',')
        meta['width'] = int(width)
        meta['height'] = int(height)
    else:
        meta['width'] = 0
        meta['height'] = 0
    if to_native and el.attrs.get('data-date'):
        meta['date'] = datetime.strptime(el.attrs['data-date'], IMG_DATE_FMT)
    elif to_native:
        meta['date'] = datetime(1900, 1, 1, 0, 0, 0)
    else:
        meta['date'] = el.attrs.get('data-date', '')
    return meta


def img_archive(meta: Dict[str, Any], operation: Callable, out_dir: str) -> bool:
    if not (meta and operation):
        return False

    old_name_ext = split(meta['pth'])[1]
    old_name, ext = splitext(old_name_ext)
    # normalize JPEG
    if ext == '.jpeg':
        ext = '.jpg'
    new_name = meta['id'] + ext.lower()
    if new_name == old_name:
        return False

    op_name = (operation.__name__ or '').rstrip('2')
    out_dir = out_dir.rstrip('/')
    out_dir += f'/{new_name[0]}'
    new_file = f'{out_dir}/{new_name}'
    if isfile(new_file):
        log.debug(f'skipping {op_name} of {old_name_ext}, because {new_name} is a file')
        return False
    if not isdir(out_dir):
        mkdir(out_dir)

    log.debug(f'{op_name}: {old_name_ext}  ->  {new_name}')
    operation(meta['pth'], new_file)
    # update new location
    meta['pth'] = new_file
    return True


def get_img_date(img: Image.Image, fmt=IMG_DATE_FMT, fallback1=True):
    """
    Function to extract the date from a picture.
    The date is very important in many apps, including Adobe Lightroom, macOS Photos and Google Photos.
    For that reason, img-DB also uses the date to sort the images (by default).
    """
    exif = img._getexif()  # type: ignore
    meta = getattr(img, 'applist', None)
    if not exif and not meta:
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

    if fallback1:
        xmp_fmt = '%Y-%m-%dT%H:%M:%S%z'
        for _, content in meta:   # type: ignore
            marker, body = content.split(b'\x00', 1)
            if b'//ns.adobe.com/xap/' in marker:
                xmp = BeautifulSoup(body, 'xml')
                el = xmp.find(lambda x: x.has_attr('xmp:MetadataDate'))
                if el:
                    dt = datetime.strptime(el.attrs['xmp:MetadataDate'], xmp_fmt)
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
