from os import listdir
from shutil import copytree

from imgdb.config import Config
from imgdb.main import ren_op

IMGS = listdir('test/pics')


def test_db_rename_simple(temp_dir):
    ren_dir = f'{temp_dir}/input'
    copytree('test/pics', ren_dir)
    ren_op([ren_dir], '{sha224}', Config(c_hashes='sha224'))
    assert len(listdir(ren_dir)) == len(IMGS)


def test_db_rename_rchash(temp_dir):
    ren_dir = f'{temp_dir}/input'
    copytree('test/pics', ren_dir)
    ren_op([ren_dir], '{rchash}', Config(v_hashes='rchash'))
    assert len(listdir(ren_dir)) == len(IMGS)


def test_db_rename_dry_run(temp_dir):
    ren_dir = f'{temp_dir}/input'
    copytree('test/pics', ren_dir)
    ren_op([ren_dir], '{sha224}', Config(c_hashes='sha224', dry_run=True))
    # the images should not be renamed
    assert sorted(listdir(ren_dir)) == sorted(IMGS)
