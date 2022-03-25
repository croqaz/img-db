from .config import *
from .log import log
from .util import to_base, html_escape
from .vhash import VHASHES, array_to_string

from PIL import Image
from PIL.ExifTags import TAGS
from PIL.ImageOps import exif_transpose
from argparse import Namespace
from bs4 import BeautifulSoup
from bs4.element import Tag
from datetime import datetime
from exiftool import ExifToolHelper
from os import mkdir, stat as os_stat
from os.path import split, splitext, getsize, isfile, isdir
from pathlib import Path
from typing import Dict, Callable, Any, Union
import hashlib

HUMAN_TAGS = {v: k for k, v in TAGS.items()}


def get_attr_type(attr):
    """ Common helper to get the type of a prop/attr """
    if attr in ('width', 'height', 'bytes'):
        return int
    return str


def make_thumb(img: Image.Image, thumb_sz=256):
    thumb = exif_transpose(img)
    thumb.thumbnail((thumb_sz, thumb_sz))
    return thumb


def img_resize(img, sz: int):
    w, h = img.size
    # Don't make image bigger
    if sz > w or sz > h:
        log.warn(f"Won't enlarge {img.filename}! {sz} > {w}x{h}")
        return img
    if sz == w or sz == h:
        log.warn(f"Nothing to do to {img.filename}! {sz} = {w}x{h}")
        return img

    if w >= h:
        scale = float(sz) / float(w)
        size = (sz, int(h * scale))
    else:
        scale = float(sz) / float(h)
        size = (int(w * scale), sz)

    log.info(f'Resized {img.filename} from {w}x{h} to {size[0]}x{size[1]}')
    return img.resize(size, Image.LANCZOS)


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
        '__': make_thumb(img),
        'pth': str(pth),
        'format': img.format,
        'mode': img.mode,
        'size': img.size,
        'bytes': getsize(pth),
        'date': get_img_date(img),
        'make-model': get_make_model(img),
        # 'dominant-colors': get_dominant_color(img),
    }

    if opts.metadata:
        extra = exiftool_metadata(meta['pth'])
        for m in opts.metadata:
            if extra.get(m):
                meta[m] = extra[m]

    for algo in opts.v_hashes:
        val = VHASHES[algo](meta['__'])  # type: ignore
        if algo == 'bhash':
            meta[algo] = val
        elif algo == 'rchash':
            fill = int((DEFAULT_VHASH_SIZE ** 2) / 2.4)  # pad to same len
            meta[algo] = to_base(val, VISUAL_HASH_BASE).zfill(fill)
        else:
            meta[algo] = array_to_string(val, VISUAL_HASH_BASE)

    bin_text = open(pth, 'rb').read()
    for algo in opts.hashes:
        meta[algo] = hashlib.new(algo, bin_text,
                                 digest_size=HASH_DIGEST_SIZE).hexdigest()  # type: ignore

    # calculate img UID
    # programmatically create an f-string and eval it
    # this can be dangerous, can run arbitrary code, etc
    meta['id'] = eval(f'f"""{opts.uid}"""', meta)
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

    old_file = meta['pth']
    old_name_ext = split(old_file)[1]
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
    meta['pth'] = new_file

    if isfile(new_file):
        log.debug(f'skipping {op_name} of {old_name_ext}, because {new_name} is imported')
        return False
    if not isdir(out_dir):
        mkdir(out_dir)

    log.debug(f'{op_name}: {old_name_ext}  ->  {new_name}')
    operation(old_file, new_file)
    return True


def get_img_date(img: Image.Image, fmt=IMG_DATE_FMT, fallback1=True, fallback2=True):
    """
    Function to extract the date from a picture.
    The date is very important in many apps, including Adobe Lightroom, macOS Photos and Google Photos.
    For that reason, img-DB also uses the date to sort the images (by default).
    """
    exif = None
    if getattr(img, '_getexif', None):
        exif = img._getexif()  # type: ignore
    if exif:
        # (36867, 37521) # (DateTimeOriginal, SubsecTimeOriginal)
        # (36868, 37522) # (DateTimeDigitized, SubsecTimeDigitized)
        # (306, 37520)   # (DateTime, SubsecTime)
        tags = [
            HUMAN_TAGS['DateTimeOriginal'],   # when img was taken
            HUMAN_TAGS['DateTimeDigitized'],  # when img was stored digitally
            HUMAN_TAGS['DateTime'],           # when img file was changed
        ]
        exif_fmt = '%Y:%m:%d %H:%M:%S'
        for tag in tags:
            if exif.get(tag):
                dt = datetime.strptime(exif[tag], exif_fmt)
                return dt.strftime(fmt)

    applist = getattr(img, 'applist', None)
    if fallback1 and applist:
        for _, content in applist:  # type: ignore
            marker, body = content.split(b'\x00', 1)
            if b'//ns.adobe.com/xap/' in marker:
                el = BeautifulSoup(body, 'xml').find(lambda x: x.has_attr('xmp:MetadataDate'))
                if el:
                    date_str = el.attrs['xmp:MetadataDate']
                    try:
                        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')
                        return dt.strftime(fmt)
                    except Exception:
                        pass
                    try:
                        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M%z')
                        return dt.strftime(fmt)
                    except Exception:
                        pass

    if fallback2:
        stat = os_stat(img.filename)  # type: ignore
        dt = datetime.fromtimestamp(min(stat.st_mtime, stat.st_ctime))
        return dt.strftime(fmt)


def get_make_model(img: Image.Image, fmt=MAKE_MODEL_FMT):
    if not hasattr(img, '_getexif'):
        return
    exif = img._getexif()  # type: ignore
    if not exif:
        return
    make = exif.get(HUMAN_TAGS['Make'], '').strip().replace(' ', '-').title()
    model = exif.get(HUMAN_TAGS['Model'], '').strip().replace(' ', '-')
    if make or model:
        return html_escape(fmt.format(make=make, model=model))


def exiftool_metadata(pth: str) -> dict:
    """ Extract more metadata with Exiv2 """
    with ExifToolHelper() as et:
        result = {}
        for m in et.get_metadata(pth):
            for t, vals in EXTRA_META.items():
                for k in vals:
                    if m.get(k):
                        result[t] = m[k]
                        break
        return result


def get_dominant_color(img: Image.Image, sz=164, c1=16, c2=2):
    from .util import rgb_to_hex
    # TBH I'm not happy with this function
    img = img.copy()
    img.thumbnail((sz, sz))
    img = img.convert('P', palette=Image.ADAPTIVE, colors=c1).convert('RGB')
    img = img.resize((c2, c2), resample=0)
    return [rgb_to_hex(c) for _, c in sorted(img.getcolors(), key=lambda t: t[0])]
