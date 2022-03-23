from .img import el_meta
from .log import log
from .util import parse_query_expr
from .vhash import VHASHES

import attr
from argparse import Namespace
from base64 import b64encode
from bs4 import BeautifulSoup
from io import BytesIO
from typing import Dict, Any
import os.path

DB_TMPL = '<!DOCTYPE html><html lang="en">\n<head><meta charset="utf-8">' + \
          '<title>img-DB</title></head>\n<body>\n{}\n</body></html>'


def img_to_html(m: dict, opts: Namespace) -> str:
    props = []
    for key, val in m.items():
        if key == 'id' or key[0] == '_':
            continue
        if val is None:
            continue
        if isinstance(val, (tuple, list)):
            val = ','.join(str(x) for x in val)
        elif isinstance(val, (int, float)):
            val = str(val)
        props.append(f'data-{key}="{val}"')

    fd = BytesIO()
    _img = m['__']
    _img.thumbnail((opts.thumb_sz, opts.thumb_sz))
    _img.save(fd, format=opts.thumb_type, quality=opts.thumb_qual, optimize=True)
    m['thumb'] = b64encode(fd.getvalue()).decode('ascii')

    return f'<img id="{m["id"]}" {" ".join(props)} src="data:image/{opts.thumb_type};base64,{m["thumb"]}">\n'


def db_save(db: BeautifulSoup, fname: str):
    """ Persist DB on disk """
    imgs = db.find_all('img')
    return open(fname, 'w').write(DB_TMPL.format('\n'.join(str(el) for el in imgs)))


def db_query(db: BeautifulSoup, opts: Namespace):
    log.info(f'There are {len(db.find_all("img"))} imgs in img-DB')
    metas, imgs = db_filter(db, opts)  # noqa: F8
    from IPython import embed
    embed(colors='linux', confirm_exit=False)


def db_rem_el(db: BeautifulSoup, query: str):
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


def db_rem_attr(db: BeautifulSoup, attr: str):
    """
    Remove the ATTR from ALL images. The DB is not saved on disk.
    """
    i = 0
    for el in db.find_all('img'):
        if el.attrs.get(f'data-{attr}'):
            del el.attrs[f'data-{attr}']
            i += 1
    log.info(f'{i} attrs removed from DB')


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
        m = el_meta(el, to_native)
        if expr:
            ok = []
            for prop, func, val in expr:
                if func(m.get(prop), val):
                    ok.append(True)
                else:
                    ok.append(False)
            if ok and all(ok):
                metas.append(m)
                imgs.append(el)
        else:
            metas.append(m)
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


def db_check_pth(db: BeautifulSoup, action=None):
    """ Check all paths from DB (and optionally run an action) """
    i = 0
    for el in db.find_all('img'):
        pth = el.attrs['data-pth']
        if not os.path.isfile(pth):
            log.warn(f'Path {pth} is broken')
            i += 1
            if action:
                action(el)
    if i:
        log.warn(f'{i} paths are broken')
    else:
        log.info('All paths are working')


def db_gc(*args) -> str:
    if len(args) < 2:
        return ' '.join(args)
    log.debug(f'Merging {len(args)} DBs...')
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


def _gc_one(new_content, images: Dict[str, Any]):
    for new_img in BeautifulSoup(new_content, 'lxml').find_all('img'):
        img_id = new_img['id']
        if img_id in images:
            # the logic is to assume the second content is newer,
            # so it contains fresh & better information
            old_img = images[img_id]
            for k in sorted(new_img.attrs):
                old_img[k] = new_img.attrs[k]
        else:
            images[img_id] = new_img


DbStats = attr.make_class(
    'DbStats', attrs={
        'total': attr.ib(default=0),
        'bytes': attr.ib(default=0),
        'format': attr.ib(default=0),
        'mode': attr.ib(default=0),
        'size': attr.ib(default=0),
        'date': attr.ib(default=0),
        'make_model': attr.ib(default=0),
        'shutter_speed': attr.ib(default=0),
        'aperture': attr.ib(default=0),
        'iso': attr.ib(default=0),
        **{algo: attr.ib(default=0) for algo in VHASHES}
    })


def db_stats(db: BeautifulSoup):
    stat = DbStats()
    for el in db.find_all('img'):
        stat.total += 1
        if el.attrs.get('data-date'):
            stat.date += 1
        if el.attrs.get('data-make-model'):
            stat.make_model += 1
        if el.attrs.get('data-shutter-speed'):
            stat.shutter_speed += 1
        if el.attrs.get('data-aperture'):
            stat.aperture += 1
        if el.attrs.get('data-iso'):
            stat.iso += 1
        if el.attrs.get('data-format'):
            stat.format += 1
        if el.attrs.get('data-mode'):
            stat.mode += 1
        if el.attrs.get('data-bytes'):
            stat.bytes += 1
        if el.attrs.get('data-size'):
            stat.size += 1
        for algo in VHASHES:
            if el.attrs.get(f'data-{algo}'):
                setattr(stat, algo, getattr(stat, algo) + 1)
    report = f'''
Bytes coverage:  {(stat.bytes / stat.total * 100):.1f}%
Size coverage:   {(stat.size / stat.total * 100):.1f}%
Format coverage: {(stat.format / stat.total * 100):.1f}%
Mode coverage:   {(stat.mode / stat.total * 100):.1f}%
Date coverage:   {(stat.date / stat.total * 100):.2f}%
Maker coverage:  {(stat.make_model / stat.total * 100):.2f}%
Aperture coverage: {(stat.aperture / stat.total * 100):.2f}%
S-speed coverage:  {(stat.shutter_speed / stat.total * 100):.2f}%
'''
    for algo in VHASHES:
        report += f'{algo.title()} coverage:  {(getattr(stat, algo) / stat.total * 100):.2f}%\n'
    print(report)
    return stat
