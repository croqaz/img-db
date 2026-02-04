from os import listdir
from pathlib import Path

import pytest

from imgdb.config import Config
from imgdb.db import ImgDB
from imgdb.main import add_op, del_op

IMGS = listdir('test/pics')


def test_add(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    # test limit option
    add_op(['test/pics'], Config(dbname=dbname, limit=1, force=True))
    db = ImgDB(dbname)
    assert len(db) == 1


def test_add_deep(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    # test deep option + duplicates
    # exts + filters
    add_op(
        ['test/samples', 'test/samples/tiff'],
        Config(
            dbname=dbname,
            deep=True,
            exts='tiff',
            filter='width > 360',
        ),
    )
    db = ImgDB(dbname)
    assert len(db) == 4


def test_archive(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    archive = Path(f'{temp_dir}/archive')
    add_op(['test/pics'], Config(output=archive, operation='link', sym_links=True, shuffle=True, dbname=dbname))
    assert len(listdir(archive)) == len(IMGS)


def test_dry_run_archive(temp_dir):
    dbname = Path(f'{temp_dir}/test-x.htm')
    archive = Path(f'{temp_dir}/archive')
    add_op(['test/pics/'], Config(output=archive, dbname=dbname, dry_run=True))
    assert not dbname.is_file()
    assert not archive.is_dir()


def test_delete(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    archive = Path(f'{temp_dir}/archive')
    add_op(
        ['test/samples/jpg'],
        Config(
            operation='copy',
            output=archive,
            dbname=dbname,
            archive_subfolder_len=0,
            limit=3,
        ),
    )
    assert len(listdir(archive)) == 3
    del_op(None, Config(output=archive, dbname=dbname, filter='maker-model ~ BenQ'))
    assert len(listdir(archive)) == 2
    del_op(['96b26e8b05a756dbf061b1aef4ddaf62aeeec467dd6f3d65'], Config(output=archive, dbname=dbname))
    assert len(listdir(archive)) == 1
    db = ImgDB(dbname)
    assert len(db) == 1


def test_dry_run_delete(temp_dir):
    dbname = f'{temp_dir}/test-db.htm'
    archive = Path(f'{temp_dir}/archive')
    add_op(
        ['test/pics'],
        Config(
            operation='copy',
            output=archive,
            dbname=dbname,
            archive_subfolder_len=0,
        ),
    )
    assert len(listdir(archive)) == len(IMGS)

    # Wrong args
    with pytest.raises(ValueError):
        del_op([], Config(output=archive, dbname=dbname))

    # A bad filter that doesn't match anything
    del_op([], Config(output=archive, dbname=dbname, filter='maker-model ~ ABCD'))
    assert len(listdir(archive)) == len(IMGS)

    # Dry run delete all images
    del_op([], Config(output=archive, dbname=dbname, filter='width > 100', dry_run=True))
    assert len(listdir(archive)) == len(IMGS)

    db = ImgDB(dbname)
    assert len(db) == len(IMGS)
