from os import listdir
from shutil import copytree

from imgdb.config import Config
from imgdb.main import rename

IMGS = listdir('test/pics')


def test_db_rename_simple(temp_dir):
    ren_dir = f'{temp_dir}/input'
    copytree('test/pics', ren_dir)
    rename([ren_dir], '{sha224}', Config(uid='', c_hashes='sha224'))
    assert len(listdir(ren_dir)) == len(IMGS)


def test_db_rename_rchash(temp_dir):
    ren_dir = f'{temp_dir}/input'
    copytree('test/pics', ren_dir)
    rename([ren_dir], '{rchash}', Config(uid='', v_hashes='rchash'))
    assert len(listdir(ren_dir)) == len(IMGS)
