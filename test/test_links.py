from os import listdir

from imgdb.__main__ import add, links
from imgdb.config import Config, g_config
from imgdb.db import *
from imgdb.gallery import *

IMGS = listdir('test/pics')


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.archive = c.archive
    g_config.dbname = c.dbname
    g_config.links = c.links


def test_simple_links(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', archive='', dbname=dbname)
    out = f'{temp_dir}/xlinks/'
    links(out + '{Date:%Y-%m-%d}/{Pth.name}', sym_links=True, dbname=dbname)

    files = listdir(out)
    assert len(files) == len(IMGS)

    # should not do anything
    links(out + '{Date:%Y-%m-%d}/{Pth.name}', sym_links=True, dbname=dbname)
    assert len(files) == len(IMGS)
