"""
Creating galleries is one of the major features of img-DB.
"""
from .db import db_filter

from argparse import Namespace
from jinja2 import Environment, FileSystemLoader


def generate_gallery(db, opts: Namespace):
    env = Environment(loader=FileSystemLoader('imgdb/tmpl'))
    t = env.get_template('img_gallery.html')
    imgs = db_filter(db, opts)
    print(f'Generating a gallery with {len(imgs)} pictures...')
    with open('view_img_gallery.htm', 'w') as fd:
        fd.write(t.render(
            imgs=imgs,
            title='img-DB gallery',
        ))
