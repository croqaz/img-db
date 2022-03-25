from imgdb.db import *
from imgdb.main import main
from imgdb.__main__ import parse_args
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
    opts = parse_args(['test/pics', '--db', dbname])
    main(opts)
    db = BeautifulSoup(open(opts.db), 'lxml')
    assert len(db.find_all('img')) == len(IMGS)
    # also test db_save
    dbname2 = f'{temp_dir}/test-save.htm'
    db_save(db, dbname2)
    assert open(dbname).read() == open(dbname2).read()


def test_db_empty_filter(temp_dir):
    opts = parse_args(['test/pics', '--db', f'{temp_dir}/test-db.htm'])
    main(opts)
    db = BeautifulSoup(open(opts.db), 'lxml')
    metas, imgs = db_filter(db, opts)
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)


def test_db_rem(temp_dir):
    opts = parse_args(['test/pics', '--db', f'{temp_dir}/test-db.htm', '--v-hashes', 'ahash,dhash'])
    main(opts)
    db = BeautifulSoup(open(opts.db), 'lxml')
    i = db_rem_el(db, 'format = PNG')
    assert i == 1
    assert len(db.find_all('img')) == len(IMGS) - 1

    db = BeautifulSoup(open(opts.db), 'lxml')
    db_rem_el(db, 'width < 690')
    assert i == 1
    assert len(db.find_all('img')) == len(IMGS) - 1

    db = BeautifulSoup(open(opts.db), 'lxml')
    metas, _ = db_filter(db, opts)
    assert any(x.get('dhash') for x in metas)
    i = db_rem_attr(db, 'dhash')
    assert i == len(IMGS)
    metas, _ = db_filter(db, opts)
    assert any(x.get('dhash') for x in metas) == False
