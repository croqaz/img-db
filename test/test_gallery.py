from os import listdir

from imgdb.config import Config
from imgdb.main import add, generate_gallery

IMGS = listdir('test/pics')


def test_simple_gallery(temp_dir):
    c = Config(gallery=f'{temp_dir}/simple_gallery.html', dbname=f'{temp_dir}/test-db.htm')
    add(['test/pics'], c)
    generate_gallery(c)

    files = sorted(listdir(temp_dir))
    assert files == ['simple_gallery-01.html', 'test-db.htm']
    txt = open(f'{temp_dir}/simple_gallery-01.html').read()  # NOQA
    assert txt.count('<img data') == len(IMGS)


def test_gallery_add_del_attrs(temp_dir):
    c = Config(gallery=f'{temp_dir}/another_gallery', dbname=f'{temp_dir}/test-db.htm', v_hashes='ahash')
    add(['test/pics'], c)
    generate_gallery(c)

    files = sorted(listdir(temp_dir))
    assert files == ['another_gallery-01.htm', 'test-db.htm']
    txt = open(f'{temp_dir}/another_gallery-01.htm').read()  # NOQA
    assert txt.count('data-ahash') == len(IMGS)
    assert txt.count('class="rounded"') == 0

    c.add_attrs = 'class=rounded'
    c.del_attrs = 'data-ahash'
    generate_gallery(c)
    txt = open(f'{temp_dir}/another_gallery-01.htm').read()  # NOQA
    assert txt.count('data-ahash') == 0
    assert txt.count('class="rounded"') == len(IMGS)
