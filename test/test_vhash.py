from PIL import Image

from imgdb.util import make_thumb
from imgdb.vhash import run_vhash

HASHES = ('ahash', 'dhash', 'vhash', 'rchash')


def prepare_thumbs(img: Image.Image) -> dict[str, Image.Image]:
    images: dict[str, Image.Image] = {}
    for sz in (64, 256):
        images[f'{sz}px'] = make_thumb(img, sz)
    return images


def test_hashes():
    # a black image
    img = Image.new('RGB', (70, 70), (0, 0, 0))
    images = prepare_thumbs(img)
    for algo in ('ahash', 'dhash', 'vhash', 'phash'):
        assert set(run_vhash(images, algo)) == {'0'}
    b_hash = run_vhash(images, 'bhash')
    assert b_hash != '' and len(b_hash) == 36
    del img

    # a white image
    img = Image.new('RGB', (70, 70), (254, 254, 254))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    assert set(run_vhash(images, 'phash')) == {'0', '8'}
    w_hash = run_vhash(images, 'bhash')
    assert w_hash != '' and len(w_hash) == 36
    del img

    assert b_hash != w_hash

    # a red image
    img = Image.new('RGB', (70, 70), (254, 0, 0))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    assert set(run_vhash(images, 'phash')) == {'0', '8'}
    del img

    # a green image
    img = Image.new('RGB', (70, 70), (0, 254, 0))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    assert set(run_vhash(images, 'phash')) == {'0', '8'}
    del img

    # a blue image
    img = Image.new('RGB', (70, 70), (0, 0, 254))
    images = prepare_thumbs(img)
    for algo in HASHES:
        assert set(run_vhash(images, algo)) == {'0'}
    assert set(run_vhash(images, 'phash')) == {'0', '8'}
