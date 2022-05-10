"""
Creating galleries is one of the major features of img-DB.
"""
from .config import g_config
from .db import db_filter
from .log import log
from .util import slugify

from bs4 import BeautifulSoup
from jinja2 import Environment, FileSystemLoader
from os.path import splitext


def generate_gallery(db: BeautifulSoup, c=g_config):
    """
    Examples of filters:
    - date >= 2020 ; date <= 2021   -- to filter specific years
    - format = PNG ; bytes > 100000 -- to filter by format and disk-size
    - width > 5000 ; height > 4000  -- to filter by image width & height
    - make-model ~~ Sony            -- to filter by maker & model (case insensitive)
    - date ~ 2[0-9]{3}-12-25        -- to filter any year with December 25 (Christmas)
    """
    env = Environment(loader=FileSystemLoader(['tmpl', 'imgdb/tmpl']))
    t = env.get_template(c.tmpl)
    t.globals.update({'slugify': slugify})
    metas, imgs = db_filter(db, c)

    max_pages = len(metas) // c.wrap_at
    log.info(f'Generating {max_pages+1} galleries from {len(metas):,} pictures...')

    # add or remove attrs before publishing gallery
    for img in imgs:
        for a in c.del_attrs:
            if a in img.attrs:
                del img.attrs[a]
        for a in c.add_attrs:
            k, v = a.split('=')
            img.attrs[k] = v

    i = 1
    name, ext = splitext(c.gallery)
    if not ext:
        ext = '.htm'
    page_name = lambda n: f'{name}-{n:02}{ext}'
    while i <= max_pages + 1:
        next_page = ''
        if i <= max_pages:
            next_page = page_name(i + 1)
        with open(page_name(i), 'w') as fd:
            log.debug(f'Writing {page_name(i)}')
            fd.write(
                t.render(
                    imgs=imgs[(i - 1) * c.wrap_at:i * c.wrap_at],
                    metas=metas[(i - 1) * c.wrap_at:i * c.wrap_at],
                    next_page=next_page,
                    page_nr=i,
                    title='img-DB gallery',
                ))
        i += 1
