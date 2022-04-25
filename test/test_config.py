from imgdb.__main__ import add, gallery, links
from imgdb.config import *
from imgdb.db import *
from os import listdir
from os.path import split
import pytest


def teardown_module(_):
    # reset global state after run
    c = Config()
    g_config.archive = c.archive
    g_config.dbname = c.dbname
    g_config.gallery = c.gallery
    g_config.links = c.links


@pytest.fixture(scope='function')
def cfg_json(temp_dir):
    p = f'{temp_dir}/config.json'
    with open(p, 'w') as fd:
        json.dump({'thumb_sz': 74, 'hashes': 'blake2b, sha224', 'v_hashes': 'ahash'}, fd)
    yield p


def test_simple_config(cfg_json):
    c = Config(**load_config_args(cfg_json))
    assert c.thumb_sz == 74
    assert c.hashes == ['blake2b', 'sha224']
    assert c.v_hashes == ['ahash']


def test_gallery_config(cfg_json):
    temp_dir = split(cfg_json)[0]
    dbname = f'{temp_dir}/test-db.htm'

    add('test/pics', archive='', v_hashes='phash', dbname=dbname, config=cfg_json)
    db = db_open(dbname)
    assert db.img.attrs['data-blake2b']
    assert db.img.attrs['data-sha224']
    assert db.img.attrs['data-phash']
    assert not db.img.attrs.get('data-ahash')

    add('test/pics', archive='', dbname=dbname, config=cfg_json)
    db = db_open(dbname)
    assert db.img.attrs['data-ahash']

    with open(cfg_json, 'w') as fd:
        json.dump({'exts': 'png'}, fd)
    gallery(f'{temp_dir}/simple_gallery', dbname=dbname, config=cfg_json)
    imgs = db_rescue(f'{temp_dir}/simple_gallery-01.htm')
    assert len(imgs) == 1


def test_links_config(cfg_json):
    temp_dir = split(cfg_json)[0]
    dbname = f'{temp_dir}/test-db.htm'
    add('test/pics', archive='', dbname=dbname, config=cfg_json)

    with open(cfg_json, 'w') as fd:
        json.dump({'exts': 'png', 'sym_links': True}, fd)
    out = f'{temp_dir}/xlinks/'
    links(out + '{Date:%Y-%m}/{Pth.name}', dbname=dbname, config=cfg_json)
    files = listdir(out)
    assert len(files) == 1
