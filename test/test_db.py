from imgdb.db import *
from imgdb.main import main
from imgdb.__main__ import parse_args
from os import listdir, unlink

IMGS = listdir('test/pics')


def test_db_create():
    opts = parse_args(['test/pics', '--db', 'tmp1-test-db.htm'])
    main(opts)
    db = BeautifulSoup(open(opts.db), 'lxml')
    assert len(db.find_all('img')) == len(IMGS)
    unlink(opts.db)


def test_db_empty_filter():
    opts = parse_args(['test/pics', '--db', 'tmp2-test-db.htm'])
    main(opts)
    db = BeautifulSoup(open(opts.db), 'lxml')
    metas, imgs = db_filter(db, opts)
    assert len(metas) == len(IMGS)
    assert len(imgs) == len(IMGS)
    unlink(opts.db)
