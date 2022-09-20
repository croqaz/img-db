from imgdb.__main__ import rename
from os import listdir, makedirs
from shutil import copytree

IMGS = listdir('test/pics')


def test_db_rename_simple(temp_dir):
    in_dir = f'{temp_dir}/input'
    out_dir = f'{temp_dir}/output'
    copytree('test/pics', in_dir)
    rename(in_dir, output=out_dir, name='{sha224}', hashes='sha224', verbose=True)
    assert len(listdir(out_dir)) == len(IMGS)


def test_db_rename_deep(temp_dir):
    in_dir = f'{temp_dir}/input'
    out_dir = f'{temp_dir}/output'
    makedirs(f'{in_dir}/a/b/c')
    makedirs(out_dir)
    copytree('test/pics', f'{in_dir}/a/b/c', dirs_exist_ok=True)
    # rename without deep shouldn't copy anything
    rename(in_dir, output=out_dir, name='{blake2b}')
    assert len(listdir(out_dir)) == 0
    # rename with deep must copy everything
    rename(in_dir, output=out_dir, name='{sha256}', hashes='sha256', deep=True, shuffle=True)
    assert len(listdir(out_dir)) == len(IMGS)


def test_db_rename_rchash(temp_dir):
    in_dir = f'{temp_dir}/input'
    out_dir = f'{temp_dir}/output'
    copytree('test/pics', in_dir)
    rename(in_dir, output=out_dir, name='{rchash}', v_hashes='rchash')
    assert len(listdir(out_dir)) == len(IMGS)
