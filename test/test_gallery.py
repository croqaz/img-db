from imgdb.__main__ import add, gallery
from imgdb.config import g_config, Config
from imgdb.db import *
from imgdb.gallery import *
from os import listdir


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.archive = c.archive
    g_config.dbname = c.dbname
    g_config.gallery = c.gallery


def test_simple_gallery(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', archive='', dbname=dbname)
    gallery('simple_gallery', output=temp_dir, dbname=dbname)

    files = listdir(temp_dir)
    assert files == ['simple_gallery-00.htm', 'test-db.htm']