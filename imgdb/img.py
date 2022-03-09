import re
from pathlib import Path
from argparse import Namespace
from datetime import datetime
from PIL.ExifTags import TAGS
from PIL import Image
from jinja2 import Environment, FileSystemLoader

from .util import rgb_to_hex, html_escape

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
    make = exif.get(HUMAN_TAGS['Make'], '').strip().replace(' ', '-').title()
    model = exif.get(HUMAN_TAGS['Model'], '').strip().replace(' ', '-')
    return html_escape(fmt.format(make=make, model=model))


def get_dominant_color(img: Image.Image, sz=164, c1=16, c2=2):
    # TBH I'm not happy with this function
    img = img.copy()
    img.thumbnail((sz, sz))
    img = img.convert('P', palette=Image.ADAPTIVE, colors=c1).convert('RGB')
    img = img.resize((c2, c2), resample=0)
    return [rgb_to_hex(c) for _, c in sorted(img.getcolors(), key=lambda t: t[0])]


def export_img_gallery_html(db, opts: Namespace):
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_gallery.html')

    imgs = []
    for el in db.find_all('img'):
        p = Path(el.attrs.get('data-pth', ''))
        if opts.exts and p.suffix.lower() not in opts.exts:
            continue
        # if opts.filter and not re.search(opts.filter, str(p.parent / p.name)):
        #     continue
        if opts.limit and opts.limit > 0 and len(imgs) >= opts.limit:
            break
        imgs.append(el)

    with open('view_img_gallery.htm', 'w') as fd:
        fd.write(t.render(
            imgs=imgs,
            title='img-DB gallery',
        ))
