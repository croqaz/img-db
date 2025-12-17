import hashlib
from base64 import b64encode
from datetime import datetime
from io import BytesIO
from os.path import getsize, isfile, split, splitext
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from bs4.element import Tag
from PIL import ExifTags, Image
from PIL.ExifTags import TAGS
from PIL.ImageOps import exif_transpose

from .algorithm import ALGORITHMS
from .config import EXTRA_META, IMG_ATTRS_LI, IMG_DATE_FMT, g_config
from .log import log
from .vhash import VHASHES, vis_hash

HUMAN_TAGS = {v: k for k, v in TAGS.items()}


def make_thumb(img: Image.Image, thumb_sz=64) -> Image.Image:
    thumb = img.copy()
    if getattr(thumb, '_getexif', None):
        thumb = exif_transpose(thumb)  # type: ignore
    thumb.thumbnail((thumb_sz, thumb_sz))
    return thumb


def img_resize(img: Image.Image, sz: int) -> Image.Image:
    w, h = img.size
    fname = img.filename  # type: ignore
    # Don't make image bigger
    if sz > w or sz > h:
        log.warning(f"Won't enlarge {fname}! {sz} > {w}x{h}")
        return img
    if sz == w or sz == h:
        log.warning(f'Nothing to do to {fname}! {sz} = {w}x{h}')
        return img

    if w >= h:
        scale = float(sz) / float(w)
        size = (sz, int(h * scale))
    else:
        scale = float(sz) / float(h)
        size = (int(w * scale), sz)

    log.info(f'Resized {fname} from {w}x{h} to {size[0]}x{size[1]}')
    return img.resize(size, Image.Resampling.LANCZOS)


def img_to_meta(pth: Path, c=g_config):
    """Extract meta-data from a disk image."""
    try:
        img = Image.open(pth)
    except Exception as err:
        log.error(f"Cannot open image '{pth.name}'! ERROR: {err}")  # type: ignore
        return None, {}

    meta: dict[str, Any] = {
        'pth': str(pth),
        'format': img.format,
        'mode': img.mode,
        'size': img.size,
        'bytes': getsize(pth),
    }

    extra_info = pil_xmp(img)
    extra_info.update(pil_exif(img))

    if isinstance(pth, str):
        pth = Path(pth)

    stat = pth.stat()
    img_date = datetime.fromtimestamp(min(stat.st_mtime, stat.st_ctime))
    try:
        img_date = get_img_date(extra_info) or img_date
    except Exception as err:
        log.error(f"Cannot extract date '{pth.name}'! ERROR: {err}")
        return None, {}
    meta['date'] = img_date.strftime(IMG_DATE_FMT)

    try:
        meta['maker-model'] = get_maker_model(extra_info)
    except Exception as err:
        log.warning(f"Cannot extract maker-model '{pth.name}'! ERROR: {err}")

    if c.metadata is not None:
        meta['__e'] = extra_info
        for k in c.metadata:
            if k == 'aperture':
                meta[k] = get_aperture(extra_info)
            elif k == 'focal-length':
                meta[k] = get_focal_length(extra_info)
            elif k == 'shutter-speed':
                meta[k] = get_shutter_speed(extra_info)
            elif k == 'lens-maker-model':
                meta[k] = get_lens_maker_model(extra_info)
            elif k == 'iso':
                meta[k] = int(extra_info.get('ISOSpeedRatings', 0))
            elif extra_info.get(k):
                meta[k] = extra_info[k]

    if c.filter:
        m = dict(meta)
        m['width'] = img.size[0]
        m['height'] = img.size[1]
        ok = (func(m.get(prop, ''), val) for prop, func, val in c.filter)
        if not all(ok):
            log.debug(f"Img '{pth.name}' filter failed")
            return img, {}

    _thumb = make_thumb(img, c.thumb_sz)
    meta['__t'] = _thumb

    # resize to recommended size for model prediction
    _t224 = make_thumb(img, 224)
    for algo in c.algorithms:
        val = None
        try:
            val = ALGORITHMS[algo](_t224)
        except Exception as err:
            log.error(f'Error running {algo}: {err}')
        if val:
            meta[algo] = val

    # important to generate the small thumb from the original IMG!
    # if we don't, some VHASHES will be different
    _t64 = make_thumb(img, 64)
    for algo in c.v_hashes:
        meta[algo] = vis_hash(_t64, algo)

    # generate the crypto hash from the image content
    # this doesn't change when the EXIF, or XMP of the image changes
    bin_text = img.tobytes()
    for algo in c.c_hashes:
        if algo[:5] == 'blake':
            meta[algo] = hashlib.new(algo, bin_text, digest_size=c.hash_digest_size).hexdigest()  # type: ignore
        else:
            meta[algo] = hashlib.new(algo, bin_text).hexdigest()

    # calculate img UID
    # programmatically create an f-string and eval it
    # this can be dangerous, can run arbitrary code, innocent kittens can die, etc
    if c.uid:
        meta['id'] = eval(f'f"""{c.uid}"""', dict(meta))
    return img, meta


def el_to_meta(el: Tag, native=True) -> dict[str, Any]:
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
        'format': el.attrs.get('data-format', ''),
        'mode': el.attrs.get('data-mode', ''),
        'bytes': int(el.attrs.get('data-bytes', 0)),
        'date': el.attrs.get('data-date', ''),  # date as string
        'maker-model': el.attrs.get('data-maker-model', ''),
    }
    if native:
        meta['Pth'] = Path(pth)
        if meta['date']:
            meta['Date'] = datetime.strptime(el.attrs['data-date'], IMG_DATE_FMT)
        else:
            meta['Date'] = datetime(1900, 1, 1, 0, 0, 0)

    # load custom attrs first
    for k in el.attrs:
        if not k.startswith('data-'):
            continue
        if k[5:] in IMG_ATTRS_LI:
            continue
        # this will always be str
        meta[k[5:]] = el.attrs[k]

    # load supported attrs second,
    # to overwrite any custom ones
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
    # IDEA: add thumb width=xyz height=abc ?
    return f'<img id="{m["id"]}" {" ".join(props)} src="data:image/{c.thumb_type};base64,{_thumb}">\n'


def img_archive(meta: dict[str, Any], c=g_config) -> bool:
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
    if c.archive_subfolder_len > 0:  # NOQA: SIM108
        out_dir = c.output / new_name[0 : c.archive_subfolder_len]
    else:
        out_dir = c.output
    new_file = f'{out_dir}/{new_name}'
    meta['pth'] = new_file

    if not c.force and isfile(new_file):
        log.debug(f'skipping {c.operation} of {old_name_ext}, because {new_name} exists')
        return False
    if not c.dry_run and not out_dir.is_dir():
        out_dir.mkdir(parents=True)

    log.debug(f'{c.operation}: {old_name_ext}  ->  {new_name}')
    if not c.dry_run:
        try:
            c.add_func(old_path, new_file)
        except Exception as err:
            log.error(f'Cannot {c.operation} {old_name_ext} to {new_name}! ERROR: {err}')
            return False
    return True


def pil_exif(img: Image.Image) -> dict:
    extra_info: dict[Any, Any] = {}
    img_exif = img.getexif()
    for k, v in img_exif.items():
        if k == 700:  # XMLPacket
            continue
        # print(TAGS.get(k, k), ':', v)
        extra_info[TAGS.get(k, k)] = v
    for k, v in img_exif.get_ifd(ExifTags.IFD.Exif).items():
        extra_info[TAGS.get(k, k)] = v
    for k, v in img_exif.get_ifd(ExifTags.IFD.IFD1).items():
        extra_info[TAGS.get(k, k)] = v
    for k, v in extra_info.items():
        if isinstance(v, str):
            v = v.strip(' \t\n')
            v = v.split('\x00')[0]
        if isinstance(v, bytes):
            v = v.strip(b' \t\n')
            v = v.split(b'\x00')[0]
        extra_info[k] = v
    return extra_info


def pil_xmp(img: Image.Image) -> dict:
    KNOWN_ATTRS = (
        'dc:creator',
        'dc:description',
        'dc:format',
        'dc:title',
        'photoshop:ICCProfile',
        'xap:CreateDate',
        'xap:CreatorTool',
        'xap:MetadataDate',
        'xmp:CreateDate',
        'xmp:CreatorTool',
        'xmp:MetadataDate',
    )
    extra_info: dict[Any, Any] = {}
    app_list = getattr(img, 'applist', {})
    for k, content in app_list:  # type: ignore
        if k != 'APP1':
            continue
        marker, body = content.split(b'\x00', 1)
        if b'//ns.adobe.com/xap/' in marker:
            xml = BeautifulSoup(body, 'xml')
            for tag in KNOWN_ATTRS:
                el = xml.find(tag)
                if el and el.text:
                    extra_info[tag] = el.text.strip(' \t\n')
            for tag in KNOWN_ATTRS:
                el = xml.find(attrs={tag: True})
                if el:
                    extra_info[tag] = el.attrs[tag]
    return extra_info


DT_EXIF_FMT = '%Y:%m:%d %H:%M:%S'
DT_EXIF_NAMES = ('DateTimeOriginal', 'DateTimeDigitized', 'DateTime')
DT_XMP_NAMES = ('xap:CreateDate', 'xap:MetadataDate', 'xmp:CreateDate', 'xmp:MetadataDate')


def get_img_date(m: dict[str, Any]) -> datetime | None:
    """
    Function to extract the date from a picture.
    The date is very important in many apps, including macOS Photos, Google Photos, Adobe Lightroom.
    For that reason, img-DB also uses the date to sort the images (by default).
    """
    # EXIF tags
    for tag in DT_EXIF_NAMES:
        if m.get(tag):
            return datetime.strptime(m[tag], DT_EXIF_FMT)
    # XMP tags
    for tag in DT_XMP_NAMES:
        if m.get(tag):
            return datetime.fromisoformat(m[tag])


def get_maker_model(m: dict[str, Any]) -> str:
    maker = ''
    model = ''
    if m.get('Make'):
        maker = m['Make'].strip(' .\t\x00')
    if m.get('Model'):
        model = m['Model'].strip(' .\t\x00')
        if model[0] == '<':
            model = model[1:]
        if model[-1] == '>':
            model = model[:-1]
    return _post_process_mm(maker, model)


def get_lens_maker_model(m: dict[str, Any]) -> str:
    maker = ''
    model = ''
    if m.get('LensMake'):
        maker = m['LensMake'].strip(' .\t\x00')
    if m.get('LensModel'):
        model = m['LensModel'].strip(' .\t\x00')
        if model[0] == '<':
            model = model[1:]
        if model[-1] == '>':
            model = model[:-1]
    return _post_process_mm(maker, model)


def _post_process_mm(maker: str, model: str) -> str:
    maker = maker.replace(' ', '-')
    model = model.replace(' ', '-')
    maker_lower = maker.lower()
    model_lower = model.lower()
    if maker_lower == 'unknown':
        maker = ''
        maker_lower = ''
    elif maker_lower == 'casio' or maker_lower.startswith('casio-'):
        maker = 'Casio'
        maker_lower = 'casio'
    elif maker_lower.startswith('eastman-kodak'):
        maker = maker[13:]
        maker_lower = maker.lower()
    elif maker_lower == 'nikon' or maker_lower.startswith('nikon-'):
        maker = 'Nikon'
        maker_lower = 'nikon'
    elif maker_lower == 'olympus' or maker_lower.startswith('olympus-'):
        maker = 'Olympus'
        maker_lower = 'olympus'
    elif maker_lower == 'panasonic':
        maker = 'Panasonic'
    elif maker_lower == 'sony' or maker_lower.startswith('sony-'):
        maker = 'Sony'
        maker_lower = 'sony'
    elif maker_lower == 'samsung' or maker_lower.startswith('samsung-'):
        maker = 'Samsung'
        maker_lower = 'samsung'
    elif maker_lower == 'sanyo' or maker_lower.startswith('sanyo-'):
        maker = 'Sanyo'
        maker_lower = 'sanyo'
    if maker_lower.endswith('company'):
        maker = maker[:-8]
        maker_lower = maker.lower()
    elif maker_lower.endswith('corporation'):
        maker = maker[:-12]
        maker_lower = maker.lower()
    if model_lower.endswith('zoom-digital-camera'):
        model = model[:-20]
        model_lower = model.lower()
    elif model_lower.endswith('(2nd-generation)'):
        model = model[:-16] + '2nd'
        model_lower = model.lower()
    elif model_lower.endswith('(3rd-generation)'):
        model = model[:-16] + '3rd'
        model_lower = model.lower()
    elif model_lower.endswith(',-samsung-#1-mp3'):
        model = model[:-16]
        model_lower = model.lower()
    if maker and model and model_lower.startswith(maker_lower):
        model = model[len(maker) + 1 :]
    if maker or model:
        return f'{maker}-{model}'.strip('-')
    return ''


def get_aperture(m: dict[str, Any]) -> str | None:
    if m.get('FNumber'):
        frac = float(m['FNumber'])
        return f'f/{round(frac, 1)}'
    if m.get('Aperture'):
        frac = float(m['Aperture'])
        return f'f/{round(frac, 1)}'
    if m.get('ApertureValue'):
        frac = float(m['ApertureValue'])
        return f'f/{round(frac, 1)}'


def get_focal_length(m: dict[str, Any]) -> str | None:
    """Lens focal length, in mm."""
    if m.get('FocalLength'):
        ratio = float(m['FocalLength'])
        return f'{round(ratio, 1)}mm'


def get_shutter_speed(m: dict[str, Any]) -> str | None:
    if m.get('ExposureTime'):
        ratio = m['ExposureTime']
        if ratio.numerator and ratio.numerator > 1:
            frac = round(ratio.denominator / ratio.numerator)
            return f'1/{frac}s'
        if ratio.numerator == 1:
            return f'1/{ratio.denominator}s'
    if m.get('ShutterSpeed'):
        speed = round(2 ** float(m['ShutterSpeed']))
        return f'1/{speed}s'
    if m.get('ShutterSpeedValue'):
        speed = round(2 ** float(m['ShutterSpeedValue']))
        return f'1/{speed}s'
