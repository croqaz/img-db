from PIL import Image

from imgdb.util import make_thumb
from imgdb.vhash import run_vhash

HASHES = ('ahash', 'dhash', 'vhash', 'rchash')


def prepare_thumbs(img: Image.Image) -> dict[str, Image.Image]:
    images: dict[str, Image.Image] = {}
    for sz in (64, 256):
        images[f'{sz}px'] = make_thumb(img, sz)
    return images


def test_flat_hashes():
    # a black image
    img = Image.new('RGB', (70, 70), (0, 0, 0))
    images = prepare_thumbs(img)
    for algo in ('ahash', 'dhash', 'vhash'):
        assert set(run_vhash(images, algo)) == {'0'}
    b_hash = run_vhash(images, 'bhash')
    assert b_hash != '' and len(b_hash) == 36
    del img

    # a white image
    img = Image.new('RGB', (70, 70), (254, 254, 254))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    w_hash = run_vhash(images, 'bhash')
    assert w_hash != '' and len(w_hash) == 36
    del img

    assert b_hash != w_hash

    # a red image
    img = Image.new('RGB', (70, 70), (254, 0, 0))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    del img

    # a green image
    img = Image.new('RGB', (70, 70), (0, 254, 0))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    del img

    # a blue image
    img = Image.new('RGB', (70, 70), (0, 0, 254))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    del img

    # a yellow image
    img = Image.new('RGB', (70, 70), (254, 254, 0))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}


def test_complex_hashes():
    # half black, half white, vertical
    img = Image.new('RGB', (70, 70), (0, 0, 0))
    for x in range(35, 70):
        for y in range(0, 70):
            img.putpixel((x, y), (254, 254, 254))
    # for debugging:
    # img.save('test/half_black_half_white_vertical.png')
    images = prepare_thumbs(img)
    # Difference Hash computations, vertically
    assert set(run_vhash(images, 'vhash')) == {'0'}
    del img

    # half black, half white, horizontal
    img = Image.new('RGB', (70, 70), (0, 0, 0))
    for x in range(0, 70):
        for y in range(35, 70):
            img.putpixel((x, y), (254, 254, 254))
    # for debugging:
    # img.save('test/half_black_half_white_horiz.png')
    images = prepare_thumbs(img)
    # Difference Hash computation, horizontally
    assert set(run_vhash(images, 'dhash')) == {'0'}
