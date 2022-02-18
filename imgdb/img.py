import io, base64
from datetime import datetime
from PIL.ExifTags import TAGS
from PIL import Image
from jinja2 import Environment, FileSystemLoader

from .util import rgb_to_hex

HUMAN_TAGS = {v: k for k, v in TAGS.items()}


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
    make = exif.get(HUMAN_TAGS['Make'], '').title()
    model = exif.get(HUMAN_TAGS['Model'], '').replace(' ', '-')
    return fmt.format(make=make, model=model)


def get_dominant_color(img: Image.Image):
    img = img.convert('RGB')
    # img = img.convert('P', palette=Image.ADAPTIVE, colors=16).convert('RGB')
    img = img.resize((2, 2), resample=0)
    pixels = sorted(img.getcolors(), key=lambda t: t[0])
    return [rgb_to_hex(c) for _, c in pixels]


def save_img_meta_as_html(img: Image.Image, meta: dict):
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('view_img.html')

    img = img.copy()
    img.thumbnail((102, 102))
    fd = io.BytesIO()
    img.save(fd, format='webp', quality=70)
    meta['thumb'] = base64.b64encode(fd.getvalue()).decode('ascii')

    with open('view_img_meta.htm', 'w') as fd:
        fd.write(t.render(
        meta=meta,
        title=f'View meta: meta["p"]',
    ))
