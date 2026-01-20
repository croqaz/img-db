from collections import Counter

import numpy
from PIL import Image

from .util import rgb_to_hex

IMG_SZ = 256
TOP_COLOR_CUT: int = 25
TOP_COLOR_CHANNELS: int = 5
TOP_CLR_ROUND_TO: int = round(255 / TOP_COLOR_CHANNELS)


def image_brightness(img: Image.Image) -> int:
    """
    Calculate image brightness metrics. Experimental.
    A white image will return 100, and black 0.
    """
    lum_img = img.convert('L')
    if img.width > IMG_SZ or img.height > IMG_SZ:
        lum_img.thumbnail((IMG_SZ, IMG_SZ))
    return int(numpy.asarray(lum_img).mean() / 255 * 100)
    # Other methods I tried:
    # return int(scipy.stats.mode(numpy.asarray(lum_img), axis=None)[0] / 255 * 100)
    # w, h = lum_img.size
    # y, x = numpy.ogrid[:h, :w]
    # lum = numpy.asarray(lum_img, dtype=numpy.float32)
    # # Center-weighted factor: 1 at center, 0 at corners
    # center_weight = 1 - ((x - w/2)**2 + (y - h/2)**2) / ((w/2)**2 + (h/2)**2)
    # center_weight = numpy.clip(center_weight, 0, 1)  # avoid negatives at edges
    # center_weighted_mean = (lum * center_weight).sum() / center_weight.sum()
    # return int(center_weighted_mean / 255 * 100)


def top_colors(img: Image.Image, cut=TOP_COLOR_CUT) -> list[str]:
    img = img.convert('RGB')
    if img.width > IMG_SZ or img.height > IMG_SZ:
        img.thumbnail((IMG_SZ, IMG_SZ))
    collect_colors = []
    for x in range(img.width):
        for y in range(img.height):
            pix: tuple[int, int, int] = img.getpixel((x, y))  # type: ignore
            collect_colors.append(closest_color(pix))
    total = len(collect_colors)
    # stat = {k: round(v / total * 100, 1) for k, v in Counter(collect_colors).items() if v / total * 100 >= cut}
    # log.info(f'Collected {len(set(collect_colors)):,} uniq colors, cut to {len(stat):,} colors')
    return [
        f'{k[-1]}={round(v / total * 100, 1)}' for k, v in Counter(collect_colors).items() if v / total * 100 >= cut
    ]


def closest_color(pair: tuple[int, int, int], split=TOP_CLR_ROUND_TO) -> tuple[int, int, int, str]:
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


# def obj_detect_yolov5(img: Image.Image):
#     results = yolov5_model(img)
#     results.print()
#     return sorted(set(n for n in results.pandas().xyxy[0]['name']))


ALGORITHMS = {
    'brightness': image_brightness,
    'top-colors': top_colors,
    # 'obj-detect-yolov5': obj_detect_yolov5,
}
