from .config import g_config, EXTRA_META, IMG_ATTRS_LI, IMG_DATE_FMT, MAKE_MODEL_FMT
from .log import log
from .util import rgb_to_hex, extract_date
from .vhash import vis_hash, VHASHES

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
from os import stat as os_stat, replace as os_replace
from os.path import split, splitext, getsize, isfile
from pathlib import Path
from typing import Any, Dict, Union, Optional
import hashlib

HUMAN_TAGS = {v: k for k, v in TAGS.items()}


def make_thumb(img: Image.Image, thumb_sz=64):
    thumb = img.copy()
    if getattr(thumb, '_getexif', None):
        thumb = exif_transpose(thumb)
    thumb.thumbnail((thumb_sz, thumb_sz))
    return thumb


def img_resize(img, sz: int) -> Image.Image:
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
        log.error(f"Cannot open image '{pth.name}'! ERROR: {err}")  # type: ignore
        return None, {}

    meta = {
        'pth': str(pth),
        'format': img.format,
        'mode': img.mode,
        'size': img.size,
        'bytes': getsize(pth),
        'make-model': get_make_model(img),
    }

    if c.metadata:
        extra = exiftool_metadata(meta['pth'])
        meta['__e'] = extra
        for k in c.metadata:
            if extra.get(k):
                meta[k] = extra[k]

    # call these functions after extracting the EXIF metadata
    meta['date'] = get_img_date(img, meta).strftime(IMG_DATE_FMT)

    if c.filter:
        m = dict(meta)
        m['width'] = img.size[0]
        m['height'] = img.size[1]
        ok = (func(m.get(prop, ''), val) for prop, func, val in c.filter)
        if not all(ok):
            log.debug(f"Img '{pth}' filter failed")
            return img, {}

    _thumb = make_thumb(img, c.thumb_sz)
    meta['__t'] = _thumb
    # the large thumb is the closest to the full IMG
    meta['top-colors'] = top_colors(_thumb)
    if not meta['top-colors']:
        del meta['top-colors']

    # important to generate the small thumb from the original IMG!
    # if we don't, some VHASHES will be different
    _t64 = make_thumb(img, 64)
    for algo in c.v_hashes:
        meta[algo] = vis_hash(_t64, algo)

    # generate the crypto hash from the image content
    # this doesn't change when the EXIF, or XMP of the image changes
    bin_text = img.tobytes()
    for algo in c.hashes:
        if algo[:5] == 'blake':
            meta[algo] = hashlib.new(algo, bin_text,
                                     digest_size=c.hash_digest_size).hexdigest()  # type: ignore
        else:
            meta[algo] = hashlib.new(algo, bin_text).hexdigest()

    # calculate img UID
    # programmatically create an f-string and eval it
    # this can be dangerous, can run arbitrary code, innocent kittens can die, etc
    if c.uid:
        meta['id'] = eval(f'f"""{c.uid}"""', dict(meta))
    return img, meta


def el_to_meta(el: Tag) -> Dict[str, Any]:
    """
    Extract meta-data from a IMG element, from imd-db.htm.
    The base name (without extension) is always the ID.
    The lower-case meta are either text, or number.
    The Title-case meta are Python native objects.
    Full file name: Pth.name
    File extension: Pth.suffix
    """
    pth = el.attrs['data-pth']
    meta = {
        'id': el.attrs['id'],
        'pth': pth,  # path as string
        'Pth': Path(pth),
        'format': el.attrs.get('data-format', ''),
        'mode': el.attrs.get('data-mode', ''),
        'bytes': int(el.attrs.get('data-bytes', 0)),
        'make-model': el.attrs.get('data-make-model', ''),
        'date': el.attrs.get('data-date', '')  # date as string
    }
    if meta['date']:
        meta['Date'] = extract_date(el.attrs['data-date'])
    else:
        meta['Date'] = datetime(1900, 1, 1, 0, 0, 0)
    for algo in VHASHES:
        if el.attrs.get(f'data-{algo}'):
            meta[algo] = el.attrs[f'data-{algo}']
    for extra in EXTRA_META:
        if el.attrs.get(f'data-{extra}'):
            if extra == 'iso':
                meta[extra] = int(el.attrs[f'data-{extra}'])
            else:
                meta[extra] = el.attrs[f'data-{extra}']
    if el.attrs.get('data-size'):
        width, height = el.attrs['data-size'].split(',')
        meta['width'] = int(width)
        meta['height'] = int(height)
    else:
        meta['width'] = 0
        meta['height'] = 0
    # load custom attrs
    for k in el.attrs:
        if not k.startswith('data-'):
            continue
        if k[5:] in IMG_ATTRS_LI:
            continue
        # this will always be str
        meta[k[5:]] = el.attrs[k]
    return meta


def meta_to_html(m: dict, c=g_config) -> str:
    fd = BytesIO()
    _img = m['__t']
    _img.save(fd, format=c.thumb_type, quality=c.thumb_qual, optimize=True)
    _thumb = b64encode(fd.getvalue()).decode('ascii')

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

    # TODO: add loading=lazy ?
    # TODO: add thumb width=xyz height=abc ?
    return f'<img id="{m["id"]}" {" ".join(props)} src="data:image/{c.thumb_type};base64,{_thumb}">\n'


def img_archive(meta: Dict[str, Any], c=g_config) -> bool:
    """
    Very important function! Copy, move, or link images into other folders.
    """
    old_path = meta['pth']
    old_name_ext = split(old_path)[1]
    old_name, ext = splitext(old_name_ext)
    # normalize exts
    ext = ext.lower()
    # normalize JPEG
    if ext == '.jpeg':
        ext = '.jpg'
    new_name = meta['id'] + ext
    if new_name == old_name:
        return False

    # special twist to create 1 chr subfolders using the new name
    if c.archive_subfolder_len > 0:
        out_dir = c.archive / new_name[0:c.archive_subfolder_len]
    else:
        out_dir = c.archive
    new_file = f'{out_dir}/{new_name}'
    meta['pth'] = new_file

    if not c.force and isfile(new_file):
        log.debug(f'skipping {c.operation} of {old_name_ext}, because {new_name} exists')
        return False
    if not out_dir.is_dir():
        out_dir.mkdir()

    log.debug(f'{c.operation}: {old_name_ext}  ->  {new_name}')
    c.add_func(old_path, new_file)
    return True


def img_rename(old_path: str, new_base_name: str, output_dir: Path, c=g_config) -> Optional[str]:
    """
    Rename (or replace) images, move them into other folders.
    Identical with archive function, but more specific.
    """
    if not isfile(old_path):
        log.warn(f'No such file: "{old_path}"')
        return None
    old_name_ext = split(old_path)[1]
    old_name, ext = splitext(old_name_ext)
    # normalize exts
    ext = ext.lower()
    # normalize JPEG
    if ext == '.jpeg':
        ext = '.jpg'
    new_name = new_base_name + ext
    if new_name == old_name:
        return None

    new_file = f'{output_dir}/{new_name}'
    if isfile(new_file) and not c.force:
        log.debug(f'skipping rename of {old_name_ext}, because {new_name} exists')
        return new_file
    if not output_dir.is_dir():
        output_dir.mkdir()

    log.debug(f'rename: {old_name_ext}  ->  {new_name}')
    # rename + replace destination
    os_replace(old_path, new_file)
    return new_file


def get_img_date(
    img: Image.Image,
    meta={},
    fallback1=True,
    fallback2=True,
    fallback3=False,
):
    """
    Function to extract the date from a picture.
    The date is very important in many apps, including Adobe Lightroom, macOS Photos and Google Photos.
    For that reason, img-DB also uses the date to sort the images (by default).
    """
    exif = None
    if getattr(img, '_getexif', None):
        exif = img._getexif()  # type: ignore

    exif_fmt = '%Y:%m:%d %H:%M:%S'
    if exif:
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
                return datetime.strptime(exif[tag], exif_fmt)

    applist = getattr(img, 'applist', None)
    if fallback1 and applist:
        for _, content in applist:  # type: ignore
            marker, body = content.split(b'\x00', 1)
            if b'//ns.adobe.com/xap/' in marker:
                el = BeautifulSoup(body, 'xml').find(lambda x: x.has_attr('xmp:MetadataDate'))
                if el:
                    date_str = el.attrs['xmp:MetadataDate']  # type: ignore
                    try:
                        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S%z')
                    except Exception:
                        pass
                    try:
                        return datetime.strptime(date_str, '%Y-%m-%dT%H:%M%z')
                    except Exception:
                        pass

    if fallback2:
        iptc_fmt = '%Y:%m:%d'
        # try to reuse the cached meta, to avoid opening the img file again
        if meta.get('__e'):
            extra = meta['__e']
        else:
            extra = exiftool_metadata(img.filename)  # type: ignore
        if extra.get('IPTC:DateCreated'):
            try:
                return datetime.strptime(extra['IPTC:DateCreated'], iptc_fmt)
            except Exception:
                pass
        elif extra.get('XMP:DateCreated'):
            try:
                return datetime.strptime(extra['XMP:DateCreated'], exif_fmt)
            except Exception:
                pass

    if fallback3:
        stat = os_stat(img.filename)  # type: ignore
        return datetime.fromtimestamp(min(stat.st_mtime, stat.st_ctime))

    return datetime(1900, 1, 1, 0, 0, 0)


def get_make_model(img: Image.Image, fmt=MAKE_MODEL_FMT):
    if not hasattr(img, '_getexif'):
        return
    exif = img._getexif()  # type: ignore
    if not exif:
        return
    make = exif.get(HUMAN_TAGS['Make'], '').strip(' \t\x00')
    make = make.replace(' ', '-').replace('_', '-').title()
    model = exif.get(HUMAN_TAGS['Model'], '').strip(' \t\x00').replace(' ', '-')
    if make and model and model.startswith(make):
        model = model[len(make) + 1:]
    # post process
    if make == 'Unknown':
        make = ''
    if make.startswith('Olympus-'):
        make = make[:7]
    elif make.startswith('Sanyo-'):
        make = make[:5]
    elif make.endswith('Company'):
        make = make[:-8]
    elif make.endswith('Corporation'):
        make = make[:-12]
    if model.endswith('ZOOM-DIGITAL-CAMERA'):
        model = model[:-20]
    elif model.endswith('(2nd-generation)'):
        model = model[:-16] + '2nd'
    elif model.endswith('(3rd-generation)'):
        model = model[:-16] + '3rd'
    # after pp
    _m = make.split('-')[-1].lower()
    if make and model and model.lower().startswith(_m):
        model = model[len(_m) + 1:]
    if make or model:
        return fmt.format(make=make, model=model).strip('-')


def exiftool_metadata(pth: str) -> dict:
    """ Extract more metadata with Exiv2 """
    with ExifToolHelper() as et:
        result = {}
        for m in et.get_metadata(pth):
            for t, vals in EXTRA_META.items():
                for k in vals:
                    if m.get(k):
                        val = m[k]
                        # make all values string, to be used later in filters
                        if isinstance(val, (tuple, list)):
                            val = ','.join(str(x) for x in val)
                        elif isinstance(val, (int, float)):
                            val = str(val)
                        result[t] = val
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
    SZ = 256
    img = img.convert('RGB')
    if img.width > SZ or img.height > SZ:
        img.thumbnail((256, 256))
    collect_colors = []
    for x in range(img.width):
        for y in range(img.height):
            collect_colors.append(closest_color(img.getpixel((x, y))))
    total = len(collect_colors)
    # stat = {k: round(v / total * 100, 1) for k, v in Counter(collect_colors).items() if v / total * 100 >= cut}
    # log.info(f'Collected {len(set(collect_colors)):,} uniq colors, cut to {len(stat):,} colors')
    return [f'{k[-1]}={round(v/total*100, 1)}' for k, v in Counter(collect_colors).items() if v / total * 100 >= cut]
