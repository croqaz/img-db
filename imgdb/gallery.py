"""
Creating galleries is one of the major features of img-DB.
"""
from .db import db_filter

from argparse import Namespace
from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader


def generate_gallery(db: BeautifulSoup, opts: Namespace):
    """
    Examples of filters:
    - date >= 2020 ; date <= 2021   -- to filter specific years
    - format = PNG ; bytes > 100000 -- to filter by format and disk-size
    - width > 5000 ; height > 4000  -- to filter by image width & height
    - make-model ~ Sony             -- to filter by maker & model
    """
    gallery = opts.gallery
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_gallery.html')
    metas, imgs = db_filter(db, opts)
    print(f'Generating a gallery with {len(metas)} pictures...')
    with open(gallery, 'w') as fd:
        fd.write(t.render(
            imgs=imgs,
            metas=metas,
            title='img-DB gallery',
        ))
