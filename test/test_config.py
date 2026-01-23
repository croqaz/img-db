import json
from os import listdir
from os.path import split
from pathlib import Path

import pytest

from imgdb.algorithm import ALGORITHMS
from imgdb.config import Config, g_config
from imgdb.db import db_open, db_rescue
from imgdb.main import add_op, generate_gallery, generate_links
from imgdb.vhash import VHASHES


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.output = c.output
    g_config.dbname = c.dbname
    g_config.gallery = c.gallery
    g_config.links = c.links


@pytest.fixture(scope='function')
def cfg_json(temp_dir):
    p = f'{temp_dir}/config.json'
    with open(p, 'w') as fd:
        json.dump({'thumb_sz': 74, 'c_hashes': 'sha224, blake2b', 'v_hashes': 'ahash'}, fd)
    yield p


def test_simple_file_config(cfg_json):
    c = Config.from_file(cfg_json)
    assert c.thumb_sz == 74
    assert c.c_hashes == ['sha224', 'blake2b']
    assert c.v_hashes == ['ahash']


def test_star_config():
    c = Config(metadata='*', algorithms='*', v_hashes='*')
    assert isinstance(c.metadata, list)
    assert isinstance(c.algorithms, list)
    assert isinstance(c.v_hashes, list)
    assert len(c.algorithms) == len(ALGORITHMS)
    assert len(c.v_hashes) == len(VHASHES)


def test_bad_file_config(temp_dir):
    with pytest.raises(ValueError):
        Config.from_file(f'{temp_dir}/bad.json')

    f = Path(f'{temp_dir}/bad.zbc')
    with pytest.raises(ValueError):
        f.touch()
        Config.from_file(str(f))


def test_gallery_config(cfg_json):
    temp_dir = split(cfg_json)[0]
    dbname = f'{temp_dir}/test-db.htm'

    add_op([Path('test/pics')], Config.from_file(cfg_json, extra={'v_hashes': 'vhash', 'dbname': dbname}))
    db = db_open(dbname)
    assert db.img.attrs['data-blake2b']
    assert db.img.attrs['data-sha224']
    assert db.img.attrs['data-vhash']
    assert not db.img.attrs.get('data-ahash')

    add_op([Path('test/pics')], Config.from_file(cfg_json, extra={'dbname': dbname}))
    db = db_open(dbname)
    assert db.img.attrs['data-ahash']

    with open(cfg_json, 'w') as fd:
        json.dump({'exts': 'png'}, fd)
    generate_gallery(
        Config.from_file(
            cfg_json,
            extra={
                'dbname': dbname,
                'gallery': f'{temp_dir}/simple_gallery',
            },
        )
    )
    imgs = db_rescue(f'{temp_dir}/simple_gallery-01.htm')
    assert len(imgs) == 1


def test_links_config(cfg_json):
    temp_dir = split(cfg_json)[0]
    dbname = f'{temp_dir}/test-db.htm'
    add_op([Path('test/pics')], Config.from_file(cfg_json, extra={'dbname': dbname}))

    out = f'{temp_dir}/xlinks/'
    with open(cfg_json, 'w') as fd:
        json.dump({'exts': 'png', 'sym_links': True}, fd)

    generate_links(
        Config.from_file(
            cfg_json,
            extra={
                'dbname': dbname,
                'links': out + '{Date:%Y-%m}/{Pth.name}',
            },
        )
    )
    files = listdir(out)
    assert len(files) == 1
