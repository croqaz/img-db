from os import listdir

from imgdb.config import Config, g_config
from imgdb.db import ImgDB, _is_valid_img, db_merge, db_split
from imgdb.main import add_op, db_op

IMGS = listdir('test/pics')


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.output = c.output
    g_config.db = c.db
    g_config.algorithms = c.algorithms
    g_config.v_hashes = c.v_hashes


def test_db_create(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    # test DB create and open
    add_op(['test/pics'], Config(db=dbname, verbose=True))
    db = ImgDB(dbname)
    assert len(db) == len(IMGS)
    assert all(_is_valid_img(el) for el in db.images)

    # also test db_save
    dbname2 = f'{temp_dir}/test-save.htm'
    db.save(dbname2)
    assert len(open(dbname).read()) == len(open(dbname2).read())  # NOQA


def test_db_split_merge(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add_op(['test/pics'], Config(db=dbname, verbose=True))
    db = ImgDB(dbname)
    li1, li2 = db_split(db, 'format = PNG')
    assert len(li1) == 1
    assert len(li2) == len(IMGS) - 1
    imgs = db_merge(li1, li2)
    assert len(imgs) == len(IMGS)


def test_db_empty_filter(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add_op(['test/pics'], Config(db=dbname))
    db = ImgDB(dbname)
    metas, imgs = db.filter()
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)


def test_db_filters(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add_op(['test/pics'], Config(db=dbname))
    g_config.filter = 'pth ~ pics'  # type: ignore
    db = ImgDB(dbname)
    metas, imgs = db.filter()
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)

    g_config.filter = ''  # type: ignore

    # it's only 1 PNG in test dir
    metas, imgs = db.filter('format = PNG ; bytes > 1000')
    assert len(metas) == 1
    assert len(imgs) == 1

    # it's only 1 small image in test dir
    metas, imgs = db.filter('bytes < 180000 ')
    assert len(metas) == 1
    assert len(imgs) == 1

    # it's only 1 image of that height in test dir
    metas, imgs = db.filter('height =  1024')
    assert len(metas) == 1
    assert len(imgs) == 1

    metas, imgs = db.filter('date  ~ 1999')
    assert len(metas) == 0
    assert len(imgs) == 0


def test_db_rem(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    add_op(['test/pics'], Config(db=dbname, algorithms='illumination', v_hashes='ahash,dhash', verbose=True))
    db = ImgDB(dbname)
    i = db.rem_elem('format = PNG')
    assert i == 1
    assert len(db) == len(IMGS) - 1

    db = ImgDB(dbname)
    i = db.rem_elem('width < 690')
    assert i == 1
    assert len(db) == len(IMGS) - 1

    metas, _ = db.filter()
    assert all(x.get('ahash') for x in metas)
    assert all(x.get('dhash') for x in metas)

    db = ImgDB(dbname)
    i = db.rem_attr('dhash')
    assert i == len(IMGS)
    metas, _ = db.filter()
    assert all(x.get('ahash') for x in metas)
    assert any(x.get('dhash') for x in metas) is False


def test_db_export(temp_dir):
    db_path = f'{temp_dir}/test-db.htm'
    add_op(['test/pics'], Config(db=db_path))

    out = f'{temp_dir}/test-db.csv'
    db_op('export', Config(db=db_path, output=out, format='csv'))
    with open(out) as fd:
        assert fd.readline().startswith('"id","pth"')
        assert len(fd.readlines()) == len(IMGS)

    out = f'{temp_dir}/test-table.htm'
    db_op('export', Config(db=db_path, output=out, format='table'))
    with open(out) as fd:
        assert fd.readline().startswith('<table style=')
        assert len(fd.readlines()) == len(IMGS) + 2

    db = ImgDB(db_path)
    stat = str(db.stats())
    assert 'bytes' in stat
    assert 'size' in stat
    assert 'format' in stat
    assert 'mode' in stat
    assert 'date' in stat


def test_broken_DBs(temp_dir):
    db_path = 'test/fixtures/broken-db1.htm'
    db = ImgDB(db_path)
    assert len(db) == 1

    db_path = 'test/fixtures/broken-db2.htm'
    db = ImgDB(db_path)
    assert len(db) == 1

    db_path = 'test/fixtures/broken-db3.htm'
    db = ImgDB(db_path)
    assert len(db) == 1

    db_path = 'test/fixtures/broken-db4.htm'
    db = ImgDB(db_path)
    assert len(db) == 2

    db_path = 'test/fixtures/broken-db5.htm'
    db = ImgDB(db_path)
    assert len(db) == 5

    db_path = f'{temp_dir}/fixed-db.htm'
    db.save(db_path)
    db = ImgDB(db_path)
    assert len(db) == 1
