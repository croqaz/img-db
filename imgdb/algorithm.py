"""
Different algorithms for image analysis and feature extraction.
"""

from collections import Counter
from typing import Any, Optional

import numpy
from blurhash_rs import blurhash_decode, blurhash_encode
from PIL import Image

from .log import log
from .util import rgb_to_hex

IMG_SZ = 256
TOP_COLOR_CUT: int = 25
TOP_COLOR_CHANNELS: int = 5
TOP_C_ROUND_TO: int = round(255 / TOP_COLOR_CHANNELS)


def image_illumination(image: Image.Image) -> float:
    """
    Calculates image brightness using illumination from HSV color space,
    adding average RGB brightness for better accuracy.
    Returns a value from 0 (dark) to 100 (bright).
    """
    img = image.convert('HSV')
    value_channel = numpy.asarray(img)[:, :, 2]
    value = numpy.mean(value_channel) / 255 * 100

    img = image.convert('RGB')
    np_img = numpy.asarray(img)
    r_channel_mean = numpy.mean(np_img[:, :, 0])
    g_channel_mean = numpy.mean(np_img[:, :, 1])
    b_channel_mean = numpy.mean(np_img[:, :, 2])
    brightness = (r_channel_mean + g_channel_mean + b_channel_mean) / 3 / 255 * 100

    return float(round((value + value + brightness) / 3, 2))


def image_saturation(image: Image.Image) -> float:
    """
    Calculates the average saturation of the image.
    Returns a value from 0 (grayscale) to 100 (vibrant).
    """
    img = image.convert('HSV')
    saturation_channel = numpy.asarray(img)[:, :, 1]
    return float(round((numpy.mean(saturation_channel) / 255 * 100), 2))


def image_intensity_range(image: Image.Image) -> float:
    """
    Calculates the intensity range of the middle 90% of pixels,
    ignoring the darkest 5% and brightest 5%.
    This gives a better sense of contrast without outliers.
    Typically from 0 (no range) to 100 (full range).
    """
    img = image.convert('L')
    np_img = numpy.asarray(img)
    p05 = numpy.percentile(np_img, 5)
    p95 = numpy.percentile(np_img, 95)
    return float(round((p95 - p05) / 255 * 100, 2))


def top_colors(image: Image.Image, cut=TOP_COLOR_CUT) -> list[str]:
    """
    Calculate top colors in the image, only if they exceed
    a certain percentage (cut) of the total pixels.
    Returns a list of strings like '#hexcode=percentage%'.
    This uses the blurred image for better results.
    """
    img = image.convert('RGB')
    collect_colors = []
    for x in range(img.width):
        for y in range(img.height):
            pix: tuple[int, int, int] = img.getpixel((x, y))  # type: ignore
            collect_colors.append(_closest_color(pix))
    total = len(collect_colors)
    # stat = {k: round(v / total * 100, 1) for k, v in Counter(collect_colors).items() if v / total * 100 >= cut}
    # log.info(f'Collected {len(set(collect_colors)):,} uniq colors, cut to {len(stat):,} colors')
    return [
        f'{k[-1]}={round(v / total * 100, 1)}' for k, v in Counter(collect_colors).items() if v / total * 100 >= cut
    ]


def _closest_color(pair: tuple[int, int, int], split=TOP_C_ROUND_TO) -> tuple[int, int, int, str]:
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


ALGORITHMS: dict[str, Any] = {
    'illumination': image_illumination,
    'saturation': image_saturation,
    'contrast': image_intensity_range,
    'top-colors': top_colors,
}


def run_algo(images: dict[str, Any], algo: str) -> Optional[str]:
    # This function is supposed to be called from img_to_meta(),
    # so images dict will always contain '64px' and larger Images.
    if algo == 'illumination' or algo == 'saturation':
        return ALGORITHMS[algo](images['64px'])
    if algo == 'contrast':
        return ALGORITHMS[algo](images['256px'])

    if 'bhash' not in images:
        # Encode blurhash from 4x4 components
        # This is used for top-colors algorithms
        images['bhash'] = blurhash_encode(images['256px'], x_components=4, y_components=4)
    if 'blur' not in images:
        images['blur'] = blurhash_decode(images['bhash'], 32, 32)

    try:
        return ALGORITHMS[algo](images['blur'])
    except Exception as err:
        log.error(f'Error running {algo}: {err}')
