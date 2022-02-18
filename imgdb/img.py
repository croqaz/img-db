from PIL import Image
from PIL.ExifTags import TAGS
from datetime import datetime

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
    # naive approach
    img = img.copy().convert('RGB')
    img = img.resize((1, 1), resample=0)
    dominant_color = img.getpixel((0, 0))
    return rgb_to_hex(dominant_color)


def get_dominant_color2(img: Image.Image, palette_size=16):
    # ref: https://stackoverflow.com/a/61730849
    img = img.copy()
    img.thumbnail((100, 100))
    paletted = img.convert('P', palette=Image.ADAPTIVE, colors=palette_size)
    color_counts = sorted(paletted.getcolors(), reverse=True)
    palette_index = color_counts[0][1]
    palette = paletted.getpalette()
    dominant_color = palette[palette_index * 3:palette_index * 3 + 3]  # type: ignore
    return rgb_to_hex(dominant_color)
