from os import listdir

from imgdb.__main__ import add, gallery
from imgdb.config import Config, g_config
from imgdb.db import *
from imgdb.gallery import *

IMGS = listdir('test/pics')


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.archive = c.archive
    g_config.dbname = c.dbname
    g_config.gallery = c.gallery


def test_simple_gallery(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', archive='', dbname=dbname)
    gallery(f'{temp_dir}/simple_gallery.html', dbname=dbname)

    files = sorted(listdir(temp_dir))
    assert files == ['simple_gallery-01.html', 'test-db.htm']
    txt = open(f'{temp_dir}/simple_gallery-01.html').read()
    assert txt.count('<img data') == len(IMGS)


def test_gallery_add_del_attrs(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', archive='', v_hashes='ahash', dbname=dbname)
    gallery(f'{temp_dir}/simple_gallery', dbname=dbname)

    files = sorted(listdir(temp_dir))
    assert files == ['simple_gallery-01.htm', 'test-db.htm']
    txt = open(f'{temp_dir}/simple_gallery-01.htm').read()
    assert txt.count('data-ahash') == len(IMGS)
    assert txt.count('class="rounded"') == 0

    gallery(f'{temp_dir}/simple_gallery', dbname=dbname, add_attrs='class=rounded', del_attrs='data-ahash')
    txt = open(f'{temp_dir}/simple_gallery-01.htm').read()
    assert txt.count('data-ahash') == 0
    assert txt.count('class="rounded"') == len(IMGS)
