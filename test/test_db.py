from imgdb.__main__ import add
from imgdb.config import g_config
from imgdb.db import *
from os import listdir
from tempfile import TemporaryDirectory
import pytest

IMGS = listdir('test/pics')


@pytest.fixture(scope='function')
def temp_dir():
    with TemporaryDirectory(prefix='imgdb-') as tmpdir:
        yield tmpdir


def test_db_create(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    # test DB create and open
    add('test/pics', dbname=dbname, verbose=True)
    db = db_open(dbname)
    assert len(db.find_all('img')) == len(IMGS)

    # also test db_save
    dbname2 = f'{temp_dir}/test-save.htm'
    db_save(db, dbname2)
    assert open(dbname).read() == open(dbname2).read()


def test_db_empty_filter(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname)
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)


def test_db_filters(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname)
    g_config.filtr = 'pth ~ pics'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)

    # it's only 1 PNG in test dir
    g_config.filtr = 'format = PNG ; bytes > 1000'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 1
    assert len(imgs) == 1

    # it's only 1 small image in test dir
    g_config.filtr = 'bytes < 180000'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 1
    assert len(imgs) == 1

    # it's only 1 image of that height in test dir
    g_config.filtr = 'height = 1024'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 1
    assert len(imgs) == 1

    g_config.filtr = 'date ~ 1999'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 0
    assert len(imgs) == 0


def test_db_rem(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname, v_hashes='ahash,dhash', verbose=True)
    db = db_open(dbname)
    i = db_rem_elem(db, 'format = PNG')
    assert i == 1
    assert len(db.find_all('img')) == len(IMGS) - 1

    db = db_open(dbname)
    db_rem_elem(db, 'width < 690')
    assert i == 1
    assert len(db.find_all('img')) == len(IMGS) - 1

    db = db_open(dbname)
    metas, _ = db_filter(db)
    assert all(x.get('ahash') for x in metas)
    assert all(x.get('dhash') for x in metas)

    i = db_rem_attr(db, 'dhash')
    assert i == len(IMGS)
    metas, _ = db_filter(db)
    assert all(x.get('ahash') for x in metas)
    assert any(x.get('dhash') for x in metas) == False
