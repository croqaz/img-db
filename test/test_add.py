from os import listdir, mkdir

from imgdb.__main__ import add
from imgdb.config import Config, g_config
from imgdb.db import *

IMGS = listdir('test/pics')


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.archive = c.archive
    g_config.dbname = c.dbname


def test_add(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'

    # test limit option
    add('test/pics', dbname=dbname, limit=1, force=True)
    db = db_open(dbname)
    assert len(db.find_all('img')) == 1

    # test deep option
    add('test', dbname=dbname, deep=True, force=True)
    db = db_open(dbname)
    assert len(db.find_all('img')) == len(IMGS)


def test_archive(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    archive = f'{temp_dir}/archive'
    mkdir(archive)

    add('test/pics', archive=archive, operation='copy', dbname=dbname)
    assert len(listdir(archive)) == len(IMGS)
