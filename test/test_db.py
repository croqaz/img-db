from imgdb.__main__ import add, db
from imgdb.config import g_config, Config
from imgdb.db import *
from os import mkdir, listdir

IMGS = listdir('test/pics')


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.archive = c.archive
    g_config.dbname = c.dbname
    g_config.algorithms = c.algorithms
    g_config.v_hashes = c.v_hashes


def test_db_create(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    # test DB create and open
    add('test/pics', dbname=dbname, verbose=True)
    db = db_open(dbname)
    assert len(db.find_all('img')) == len(IMGS)
    assert all(db_valid_img(el) for el in db.find_all('img'))

    # also test db_save
    dbname2 = f'{temp_dir}/test-save.htm'
    db_save(db, dbname2)
    assert open(dbname).read() == open(dbname2).read()


def test_db_split_merge(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname, verbose=True)
    db = db_open(dbname)
    li1, li2 = db_split(db, 'format = PNG')
    assert len(li1) == 1
    assert len(li2) == len(IMGS) - 1
    imgs = db_merge(li1, li2)
    assert len(imgs) == len(IMGS)


def test_db_empty_filter(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname)
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)


def test_db_filters(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname)
    g_config.filter = 'pth ~ pics'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)

    # it's only 1 PNG in test dir
    g_config.filter = 'format = PNG ; bytes > 1000'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 1
    assert len(imgs) == 1

    # it's only 1 small image in test dir
    g_config.filter = 'bytes < 180000 '  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 1
    assert len(imgs) == 1

    # it's only 1 image of that height in test dir
    g_config.filter = 'height =  1024'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 1
    assert len(imgs) == 1

    g_config.filter = 'date  ~ 1999'  # type: ignore
    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == 0
    assert len(imgs) == 0

    g_config.filter = ''  # type: ignore


def test_db_rem(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname, algorithms='*', v_hashes='ahash,dhash', verbose=True)
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
    assert any(x.get('dhash') for x in metas) is False


def test_db_export(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname)

    out = f'{temp_dir}/test-db.csv'
    db('export', dbname=dbname, output=out, format='csv')
    with open(out) as fd:
        assert fd.readline().startswith('"id","pth"')
        assert len(fd.readlines()) == len(IMGS)

    out = f'{temp_dir}/test-db.htm'
    db('export', dbname=dbname, output=out, format='table')
    with open(out) as fd:
        assert fd.readline().startswith('<table style')
        assert len(fd.readlines()) == len(IMGS) + 2


def test_db_rescue(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', dbname=dbname)
    # add again (update)
    add('test/pics', dbname=dbname)
    db = db_open(dbname)
    assert len(db.find_all('img')) == len(IMGS)

    db_rescue(dbname)
    db = db_open(dbname)
    assert len(db.find_all('img')) == len(IMGS)


def test_db_doctor(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    archive = f'{temp_dir}/archive'
    mkdir(archive)
    add('test/pics', archive=archive, dbname=dbname)
    g_config.archive = archive  # type: ignore
    g_config.dbname = dbname
    db_doctor()

    metas, imgs = db_filter(db_open(dbname))
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)
