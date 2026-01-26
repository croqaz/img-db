from PIL import Image

from imgdb.util import hamming_distance, hex_to_rgb, levenshtein_distance, make_thumb, rgb_to_hex, slugify


def prepare_thumbs(img: Image.Image) -> dict[str, Image.Image]:
    images: dict[str, Image.Image] = {}
    for sz in (64, 256):
        images[f'{sz}px'] = make_thumb(img, sz)
    return images


def test_slug():
    assert slugify('Hélló Wörld') == 'hello-world'
    assert slugify(' x   y  ABC ') == 'x-y-abc'


def test_distance():
    assert hamming_distance('a', 'a') == 0
    assert hamming_distance('abc', 'abx') == 1
    assert hamming_distance('abc', 'x') == float('inf')

    assert levenshtein_distance('kitten', 'sitting') == 3
    assert levenshtein_distance('', '') == 0
    assert levenshtein_distance('a', '') == 1
    assert levenshtein_distance('', 'abc') == 3


def test_rgb_hex():
    assert rgb_to_hex((0, 0, 0)) == '#000000'
    assert rgb_to_hex((255, 0, 0)) == '#ff0000'
    assert rgb_to_hex((1, 2, 3)) == '#010203'

    assert hex_to_rgb('#000000') == (0, 0, 0)
    assert hex_to_rgb('#ffff00') == (255, 255, 0)
    assert hex_to_rgb('#010203') == (1, 2, 3)
