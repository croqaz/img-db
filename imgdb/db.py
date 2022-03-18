from .img import el_meta
from .log import log
from .util import parse_query_expr

from PIL import Image
from argparse import Namespace
from base64 import b64encode
from bs4 import BeautifulSoup
from bs4.element import Tag
from io import BytesIO
from typing import Dict, Any
import os.path

DB_TMPL = '<!DOCTYPE html><html lang="en">\n<head><meta charset="utf-8">' + \
          '<title>img-DB</title></head>\n<body>\n{}\n</body></html>'


def img_to_html(img: Image.Image, m: dict, opts: Namespace) -> str:
    props = []
    for key, val in m.items():
        if key == 'id':
            continue
        if val is None:
            continue
        if isinstance(val, (tuple, list)):
            val = ','.join(str(x) for x in val)
        elif isinstance(val, (int, float)):
            val = str(val)
        props.append(f'data-{key}="{val}"')

    img = img.copy()
    img.thumbnail((opts.thumb_sz, opts.thumb_sz))
    fd = BytesIO()
    img.save(fd, format=opts.thumb_type, quality=opts.thumb_qual)
    m['thumb'] = b64encode(fd.getvalue()).decode('ascii')

    return f'<img id="{m["id"]}" {" ".join(props)} src="data:image/webp;base64,{m["thumb"]}">\n'


def db_save(db: BeautifulSoup, fname: str):
    """ Persist DB on disk """
    imgs = db.find_all('img')
    return open(fname, 'w').write(DB_TMPL.format('\n'.join(str(el) for el in imgs)))


def db_query(db: BeautifulSoup, opts: Namespace):
    log.info(f'There are {len(db.find_all("img"))} imgs in img-DB')
    metas, imgs = db_filter(db, opts)  # noqa: F8
    from IPython import embed
    embed(colors='linux', confirm_exit=False)


def db_remove(db: BeautifulSoup, query: str):
    """
    Remove from DB images that match query. The DB is not saved on disk.
    """
    expr = parse_query_expr(query)
    i = 0
    for el in db.find_all('img'):
        for prop, func, val in expr:
            ok = []
            m = el_meta(el, False)
            if func(m.get(prop), val):
                ok.append(True)
            if ok and all(ok):
                el.decompose()
                i += 1
    log.info(f'{i} imgs removed from DB')


def db_filter(db: BeautifulSoup, opts: Namespace) -> tuple:
    to_native = bool(opts.links)
    metas = []
    imgs = []
    expr = []
    if opts.filter:
        expr = parse_query_expr(opts.filter)
    for el in db.find_all('img'):
        ext = os.path.splitext(el.attrs['data-pth'])[1]
        if opts.exts and ext.lower() not in opts.exts:
            continue
        if expr:
            ok = []
            m = el_meta(el, to_native)
            for prop, func, val in expr:
                if func(m.get(prop), val):
                    ok.append(True)
                else:
                    ok.append(False)
            if ok and all(ok):
                metas.append(m)
                imgs.append(el)
        else:
            imgs.append(el)
        if opts.limit and opts.limit > 0 and len(imgs) >= opts.limit:
            break
    if imgs:
        log.info(f'There are {len(imgs)} filtered imgs')
    return metas, imgs


def db_rescue(fname1: str, fname2: str):
    """
    Rescue images from a broken DB. This is pretty slow, so it's not enabled on save.
    """
    imgs = {}
    for line in open(fname1):
        if not (line and 'img' in line):
            continue
        try:
            soup = BeautifulSoup(line, 'lxml')
            if soup.img:
                for el in soup.find_all('img'):
                    imgs[el.attrs['id']] = el
        except Exception as err:
            print('ERR:', err)
    log.info(f'Rescued {len(imgs)} imgs')
    return open(fname2, 'w').write(DB_TMPL.format('\n'.join(str(el) for el in imgs.values())))


def db_gc(*args) -> str:
    if len(args) < 2:
        return ' '.join(args)
    log.debug('DB compacting...')
    images: Dict[str, Any] = {}
    for content in args:
        _gc_one(content, images)
    elems = []
    for el in sorted(images.values(),
                     reverse=True,
                     key=lambda el: el.attrs.get('data-date', '00' + el['id'])):
        elems.append(str(el))
    log.info(f'Compacted {len(elems)} imgs')
    return DB_TMPL.format('\n'.join(elems))


def _gc_one(content, images: Dict[str, Any]):
    for img in BeautifulSoup(content, 'lxml').find_all('img'):
        img_id = img['id']
        if img_id in images:
            _merge_imgs(images[img_id], img)
        else:
            images[img_id] = img


def _merge_imgs(img1: Tag, img2: Tag):
    # the logic is to assume the second IMG is newer,
    # so it contains fresh & better information
    for key, val in img2.attrs.items():
        img1[key] = val
