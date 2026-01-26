from PIL import Image

from imgdb.algorithm import run_algo, top_colors

from .test_util import prepare_thumbs


def test_flat_hashes():
    # a black image
    img = Image.new('RGB', (70, 70), (0, 0, 0))
    images = prepare_thumbs(img)
    brightness = run_algo(images, 'illumination')
    assert brightness == 0.0
    contrast = run_algo(images, 'contrast')
    assert contrast == 0.0
    saturation = run_algo(images, 'saturation')
    assert saturation == 0.0
    del img

    # a white image
    img = Image.new('RGB', (70, 70), (255, 255, 255))
    images = prepare_thumbs(img)
    brightness = run_algo(images, 'illumination')
    assert brightness == 100.0
    contrast = run_algo(images, 'contrast')
    assert contrast == 0.0
    saturation = run_algo(images, 'saturation')
    assert saturation == 0.0
    del img

    # a gray image
    img = Image.new('RGB', (70, 70), (128, 128, 128))
    images = prepare_thumbs(img)
    brightness = run_algo(images, 'illumination')
    assert int(brightness or 0) == 50
    contrast = run_algo(images, 'contrast')
    assert contrast == 0.0
    saturation = run_algo(images, 'saturation')
    assert saturation == 0.0
    del img

    # a red image
    img = Image.new('RGB', (70, 70), (255, 0, 0))
    images = prepare_thumbs(img)
    brightness = run_algo(images, 'illumination')
    assert int(brightness or 0) == 77
    contrast = run_algo(images, 'contrast')
    assert contrast == 0.0
    saturation = run_algo(images, 'saturation')
    assert saturation == 100.0
    del img

    # a yellow image
    img = Image.new('RGB', (70, 70), (255, 255, 0))
    images = prepare_thumbs(img)
    brightness = run_algo(images, 'illumination')
    assert int(brightness or 0) == 88
    contrast = run_algo(images, 'contrast')
    assert contrast == 0.0
    saturation = run_algo(images, 'saturation')
    assert saturation == 100.0


def test_top_colors():
    img = Image.new('RGB', (32, 32))  # black
    assert top_colors(img) == ['#000000=100.0']
    img = Image.new('RGB', (32, 32), (255, 254, 250))  # almost white
    assert top_colors(img) == ['#ffffff=100.0']
    img = Image.new('RGB', (32, 32), (150, 152, 154))  # gray
    assert top_colors(img) == ['#999999=100.0']
    img = Image.new('RGB', (32, 32), (254, 254, 0))  # yellow
    assert top_colors(img) == ['#ffff00=100.0']
