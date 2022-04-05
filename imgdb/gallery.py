"""
Creating galleries is one of the major features of img-DB.
"""
from .config import g_config
from .db import db_filter
from .log import log

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader


def generate_gallery(db: BeautifulSoup, c=g_config):
    """
    Examples of filters:
    - date >= 2020 ; date <= 2021   -- to filter specific years
    - format = PNG ; bytes > 100000 -- to filter by format and disk-size
    - width > 5000 ; height > 4000  -- to filter by image width & height
    - make-model ~ Sony             -- to filter by maker & model
    """
    gallery = c.gallery
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_gallery.html')
    metas, imgs = db_filter(db, c)

    wrap_nr = 1000
    max_pages = len(metas) // wrap_nr
    log.info(f'Generating {max_pages+1} galleries from {len(metas):,} pictures...')

    i = 0
    page_name = lambda n: f'{gallery}-{n:02}.htm'
    while i <= max_pages:
        next_page = ''
        if i < max_pages:
            next_page = page_name(i + 1)
        with open(page_name(i), 'w') as fd:
            fd.write(
                t.render(
                    imgs=imgs[i * wrap_nr:(i + 1) * wrap_nr],
                    metas=metas[i * wrap_nr:(i + 1) * wrap_nr],
                    next_page=next_page,
                    page_nr=i,
                    title='img-DB gallery',
                ))
        i += 1
