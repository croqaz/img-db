"""
Creating galleries is one of the major features of img-DB.
"""
from .db import db_filter
from .util import parse_filter_expr

from argparse import Namespace
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


def export_img_gallery_html(db, opts: Namespace):
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_gallery.html')

    imgs = []
    for el in db.find_all('img'):
        p = Path(el.attrs.get('data-pth', ''))
        if opts.exts and p.suffix.lower() not in opts.exts:
            continue
        if opts.filter:
            parsed = parse_filter_expr(opts.filter)
            imgs = db_filter(db, parsed)
        if opts.limit and opts.limit > 0 and len(imgs) >= opts.limit:
            break
        imgs.append(el)

    with open('view_img_gallery.htm', 'w') as fd:
        fd.write(t.render(
            imgs=imgs,
            title='img-DB gallery',
        ))
