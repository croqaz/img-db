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
    - make-model ~~ Sony            -- to filter by maker & model (case insensitive)
    - date ~ 2[0-9]{3}-12-25        -- to filter any year with December 25 (Christmas)
    """
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_gallery.html')
    metas, imgs = db_filter(db, c)
    out = c.archive or '.'

    max_pages = len(metas) // c.wrap_at
    log.info(f'Generating {max_pages+1} galleries from {len(metas):,} pictures...')

    i = 0
    page_name = lambda n: f'{out}/{c.gallery}-{n:02}.htm'
    while i <= max_pages:
        next_page = ''
        if i < max_pages:
            next_page = page_name(i + 1)
        with open(page_name(i), 'w') as fd:
            log.debug(f'Writing {page_name(i)}')
            fd.write(
                t.render(
                    imgs=imgs[i * c.wrap_at:(i + 1) * c.wrap_at],
                    metas=metas[i * c.wrap_at:(i + 1) * c.wrap_at],
                    next_page=next_page,
                    page_nr=i,
                    title='img-DB gallery',
                ))
        i += 1
