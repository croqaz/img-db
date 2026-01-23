from collections import Counter
from typing import Any, Optional

import numpy
import requests
from blurhash_rs import blurhash_decode, blurhash_encode
from PIL import Image

from .log import log
from .util import img_to_b64, rgb_to_hex

IMG_SZ = 256
TOP_COLOR_CUT: int = 25
TOP_COLOR_CHANNELS: int = 5
TOP_CLR_ROUND_TO: int = round(255 / TOP_COLOR_CHANNELS)


def image_brightness(image: Image.Image) -> int:
    """
    Calculate image brightness metrics.
    A white image will return 100, and black 0.
    """
    lum_img = image.convert('L')
    return int(numpy.asarray(lum_img).mean() / 255 * 100)


def top_colors(image: Image.Image, cut=TOP_COLOR_CUT) -> list[str]:
    img = image.convert('RGB')
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


def obj_detect_llm(img: Image.Image) -> str:
    prompt = """
Analyze the image and list all visible objects, people, animals, text, and notable elements.
For people and animals, briefly describe what they are doing and any visible emotional expression.
Keep descriptions factual and concise.
Don't add speculation or interpretation beyond what is visible.
Don't include greetings, explanations, or questions.
Output only the description.
""".strip()
    messages = [
        {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': prompt},
                {'type': 'image_url', 'image_url': {'url': 'data:image/jpeg;base64,' + img_to_b64(img, 'jpeg', 80)}},
            ],
        }
    ]
    result = requests.post(
        'http://127.0.0.1:1234/v1/chat/completions',
        headers={'Content-Type': 'application/json'},
        json={'temperature': 0.1, 'messages': messages},
    ).json()
    if 'choices' in result and len(result['choices']) > 0:
        r = result['choices'][0]['message']['content']
        r = '. '.join(t.strip(' .') for t in r.split('\n') if t)
        print('LLM object detection result:', r)
        return r
    return ''


ALGORITHMS = {
    'brightness': image_brightness,
    'top-colors': top_colors,
    # 'obj-detect-llm': obj_detect_llm,
}


def run_algo(images: dict[str, Any], algo: str) -> Optional[str]:
    # This function is supposed to be called from img_to_meta(),
    # so images dict will always contain at least '256px' Image.
    if algo == 'obj-detect-llm':
        return obj_detect_llm(images['256px'])

    if 'bhash' not in images:
        # Encode blurhash from 4x4 components
        # This is used for brightness & top-colors algorithms
        images['bhash'] = blurhash_encode(images['256px'], x_components=4, y_components=4)
    if 'blur' not in images:
        images['blur'] = blurhash_decode(images['bhash'], 32, 32)

    try:
        return ALGORITHMS[algo](images['blur'])
    except Exception as err:
        log.error(f'Error running {algo}: {err}')
