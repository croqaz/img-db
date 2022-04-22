from imgdb.vhash import *

HASHES = ('ahash', 'dhash', 'vhash', 'phash')


def test_hashes():
    # a black image
    img = Image.new('RGB', (70, 70), (0, 0, 0))
    for algo in HASHES:
        assert set(vhash(img, algo)) == {'0'}
    del img

    # a white image
    img = Image.new('RGB', (70, 70), (254, 254, 254))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vhash(img, algo)) == {'0'}
    assert set(vhash(img, 'phash')) == {'0', '8'}
    del img

    # a red image
    img = Image.new('RGB', (70, 70), (254, 0, 0))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vhash(img, algo)) == {'0'}
    assert set(vhash(img, 'phash')) == {'0', '8'}
    del img

    # a green image
    img = Image.new('RGB', (70, 70), (0, 254, 0))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vhash(img, algo)) == {'0'}
    assert set(vhash(img, 'phash')) == {'0', '8'}
    del img

    # a blue image
    img = Image.new('RGB', (70, 70), (0, 0, 254))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vhash(img, algo)) == {'0'}
    assert set(vhash(img, 'phash')) == {'0', '8'}
