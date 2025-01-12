from os import listdir
from pathlib import Path

from imgdb.config import Config, g_config
from imgdb.db import db_open
from imgdb.main import add

IMGS = listdir('test/pics')


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.output = c.output
    g_config.dbname = c.dbname


def test_add(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'

    # test limit option
    add(['test/pics'], Config(dbname=dbname, limit=1, force=True))
    db = db_open(dbname)
    assert len(db.find_all('img')) == 1

    # # test deep option ??
    # add(Args(inputs=['test'], dbname=dbname, deep=True, force=True))
    # db = db_open(dbname)
    # assert len(db.find_all('img')) == len(IMGS)


def test_archive(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    archive = Path(f'{temp_dir}/archive')
    archive.mkdir()

    add(['test/pics'], Config(output=archive, operation='copy', dbname=dbname))
    assert len(listdir(archive)) == len(IMGS)
