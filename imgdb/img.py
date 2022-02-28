import io
import base64
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


def get_dominant_color(img: Image.Image, sz=164, c1=16, c2=2):
    # TBH I'm not happy with this function
    img = img.copy()
    img.thumbnail((sz, sz))
    img = img.convert('P', palette=Image.ADAPTIVE, colors=c1).convert('RGB')
    img = img.resize((c2, c2), resample=0)
    pixels = sorted(img.getcolors(), key=lambda t: t[0])
    return [rgb_to_hex(c) for _, c in pixels]


def export_img_details_html(metas: list):
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_details.html')

    for img, m in metas:
        img = img.copy()
        img.thumbnail((102, 102))
        fd = io.BytesIO()
        img.save(fd, format='webp', quality=70)
        m['thumb'] = base64.b64encode(fd.getvalue()).decode('ascii')

    with open('view_img_details.htm', 'w') as fd:
        fd.write(t.render(
            metas=[m for _, m in metas],
            title='img-DB details',
        ))


def export_img_gallery_html(metas: list):
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_gallery.html')

    # SIZE, TYPE, QUALITY params
    img_sz = 196
    img_type = 'webp'
    img_quality = 70

    for img, m in metas:
        img = img.copy()
        img.thumbnail((img_sz, img_sz))
        fd = io.BytesIO()
        img.save(fd, format=img_type, quality=img_quality)
        m['thumb'] = base64.b64encode(fd.getvalue()).decode('ascii')

    with open('view_img_gallery.htm', 'w') as fd:
        fd.write(t.render(
            metas=[m for _, m in metas],
            title='img-DB gallery',
        ))
