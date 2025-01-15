from os import listdir

from imgdb.config import Config
from imgdb.main import add_op, generate_links

IMGS = listdir('test/pics')


def test_simple_links(temp_dir):
    c = Config(dbname=f'{temp_dir}/test-db.htm', sym_links=True)
    add_op(['test/pics'], c)

    out = f'{temp_dir}/xlinks/'
    c.links = out + '{Date:%Y-%m-%d}/{Pth.name}'
    generate_links(c)

    files = listdir(out)
    assert len(files) == len(IMGS)

    # should not do anything
    generate_links(c)
    assert len(files) == len(IMGS)

    # should link again
    c.force = True
    generate_links(c)
    assert len(files) == len(IMGS)
