from imgdb.vhash import *

HASHES = ('ahash', 'dhash', 'vhash', 'phash')


def test_hashes():
    # a black image
    img = Image.new('RGB', (70, 70), (0, 0, 0))
    for algo in HASHES:
        assert set(vis_hash(img, algo)) == {'0'}
    b_hash = vis_hash(img, 'bhash')
    assert b_hash != '' and len(b_hash) == 28
    del img

    # a white image
    img = Image.new('RGB', (70, 70), (254, 254, 254))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vis_hash(img, algo)) == {'0'}
    assert set(vis_hash(img, 'phash')) == {'0', '8'}
    w_hash = vis_hash(img, 'bhash')
    assert w_hash != '' and len(b_hash) == 28
    del img

    assert b_hash != w_hash

    # a red image
    img = Image.new('RGB', (70, 70), (254, 0, 0))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vis_hash(img, algo)) == {'0'}
    assert set(vis_hash(img, 'phash')) == {'0', '8'}
    del img

    # a green image
    img = Image.new('RGB', (70, 70), (0, 254, 0))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vis_hash(img, algo)) == {'0'}
    assert set(vis_hash(img, 'phash')) == {'0', '8'}
    del img

    # a blue image
    img = Image.new('RGB', (70, 70), (0, 0, 254))
    for algo in ('ahash', 'dhash', 'vhash', 'rchash'):
        assert set(vis_hash(img, algo)) == {'0'}
    assert set(vis_hash(img, 'phash')) == {'0', '8'}
