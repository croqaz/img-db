from .config import g_config, EXTRA_META
from .log import log
from .util import to_base, rgb_to_hex, html_escape
from .vhash import VHASHES, array_to_string

from PIL import Image
from PIL.ExifTags import TAGS
from PIL.ImageOps import exif_transpose
from base64 import b64encode
from bs4 import BeautifulSoup
from bs4.element import Tag
from collections import Counter
from datetime import datetime
from exiftool import ExifToolHelper
from io import BytesIO
from os import stat as os_stat
from os.path import split, splitext, getsize, isfile
from pathlib import Path
from typing import Dict, Any, Union
import hashlib

HUMAN_TAGS = {v: k for k, v in TAGS.items()}

IMG_DATE_FMT = '%Y-%m-%d %H:%M:%S'
MAKE_MODEL_FMT = '{make}-{model}'


def make_thumb(img: Image.Image, c=g_config):
    thumb = exif_transpose(img)
    thumb.thumbnail((c.thumb_sz, c.thumb_sz))
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


def img_to_meta(pth: Union[str, Path], c=g_config):
    """ Extract meta-data from a disk image. """
    try:
        img = Image.open(pth)
    except Exception as err:
        log.error(f"Cannot open image '{pth}'! ERROR: {err}")
        return None, {}

    if c.ignore_sz:
        w, h = img.size
        if w < c.ignore_sz or h < c.ignore_sz:
            log.debug(f"Img '{pth}' too small: {img.size}")
            return img, {}

    _thumb = make_thumb(img)
    meta = {
        '__': _thumb,
        'pth': str(pth),
        'format': img.format,
        'mode': img.mode,
        'size': img.size,
        'bytes': getsize(pth),
        'date': get_img_date(img),
        'make-model': get_make_model(img),
        'top-colors': top_colors(_thumb),
    }

    if c.metadata:
        extra = exiftool_metadata(meta['pth'])
        for m in c.metadata:
            if extra.get(m):
                meta[m] = extra[m]

    for algo in c.v_hashes:
        val = VHASHES[algo](meta['__'])  # type: ignore
        if algo == 'bhash':
            meta[algo] = val
        elif algo == 'rchash':
            fill = int((c.visual_hash_size**2) / 2.4)  # pad to same len
            meta[algo] = to_base(val, c.visual_hash_base).zfill(fill)
        else:
            meta[algo] = array_to_string(val, c.visual_hash_base)

    bin_text = open(pth, 'rb').read()
    for algo in c.hashes:
        meta[algo] = hashlib.new(algo, bin_text,
                                 digest_size=c.hash_digest_size).hexdigest()  # type: ignore

    # calculate img UID
    # programmatically create an f-string and eval it
    # this can be dangerous, can run arbitrary code, etc
    meta['id'] = eval(f'f"""{c.uid}"""', meta)
    return img, meta


def el_to_meta(el: Tag, to_native=True):
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


def img_to_html(m: dict, c=g_config) -> str:
    props = []
    for key, val in m.items():
        if key == 'id' or key[0] == '_':
            continue
        if val is None:
            continue
        if isinstance(val, (tuple, list)):
            val = ','.join(str(x) for x in val)
        elif isinstance(val, (int, float)):
            val = str(val)
        props.append(f'data-{key}="{val}"')

    fd = BytesIO()
    _img = m['__']
    _img.thumbnail((c.thumb_sz, c.thumb_sz))
    _img.save(fd, format=c.thumb_type, quality=c.thumb_qual, optimize=True)
    m['thumb'] = b64encode(fd.getvalue()).decode('ascii')

    return f'<img id="{m["id"]}" {" ".join(props)} src="data:image/{c.thumb_type};base64,{m["thumb"]}">\n'


def img_archive(meta: Dict[str, Any], c=g_config) -> bool:
    """
    Very important function! This "archives" images by copying (or moving) and renaming.
    """
    if not (meta and c.operation and c.output):
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

    # OPTS OP ???
    op_name = opts.operation.__name__.rstrip('2')
    out_dir = c.out_dir / new_name[0]
    new_file = f'{out_dir}/{new_name}'
    meta['pth'] = new_file

    if isfile(new_file) and not c.force:
        log.debug(f'skipping {op_name} of {old_name_ext}, because {new_name} is imported')
        return False
    if not out_dir.is_dir():
        out_dir.mkdir()

    log.debug(f'{op_name}: {old_name_ext}  ->  {new_name}')
    c.operation(old_file, new_file)
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
    make = exif.get(HUMAN_TAGS['Make'], '').strip(' \t\x00').replace(' ', '-').title()
    model = exif.get(HUMAN_TAGS['Model'], '').strip(' \t\x00').replace(' ', '-')
    if make and model and model.startswith(make):
        model = model[len(make) + 1:]
    if make == 'Unknown':
        make = ''
    if make or model:
        return html_escape(fmt.format(make=make, model=model)).strip('-')


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


def closest_color(pair, split=g_config.top_clr_round_to):
    r, g, b = pair
    r = round(r / split) * split
    g = round(g / split) * split
    b = round(b / split) * split
    if r > 250:
        r = 255
    if g > 250:
        g = 255
    if b > 250:
        b = 255
    return r, g, b, rgb_to_hex((r, g, b))


def top_colors(img, cut=g_config.top_color_cut):
    img = img.convert('RGB')
    img.thumbnail((256, 256))
    collect_colors = []
    for x in range(img.width):
        for y in range(img.height):
            collect_colors.append(closest_color(img.getpixel((x, y))))
    total = len(collect_colors)
    # stat = {k: round(v / total * 100, 1) for k, v in Counter(collect_colors).items() if v / total * 100 >= cut}
    # log.info(f'Collected {len(set(collect_colors)):,} uniq colors, cut to {len(stat):,} colors')
    return [f'{k[-1]}={round(v/total*100, 1)}' for k, v in Counter(collect_colors).items() if v / total * 100 >= cut]
