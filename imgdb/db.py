from .config import g_config
from .img import el_to_meta
from .log import log
from .util import parse_query_expr
from .vhash import VHASHES

from bs4 import BeautifulSoup
from typing import Dict, Any
import attr
import os.path

DB_TMPL = '<!DOCTYPE html><html lang="en">\n<head><meta charset="utf-8">' + \
          '<title>img-DB</title></head>\n<body>\n{}\n</body></html>'


def _db_or_elems(x):
    if isinstance(x, BeautifulSoup):
        return x.find_all('img')
    elif isinstance(x, (list, tuple)):
        return x
    elif isinstance(x, str):
        return BeautifulSoup(x, 'lxml').find_all('img')
    else:
        raise Exception(f'Internal error! Invalid param type {type(x)}')


def db_open(fname: str):
    return BeautifulSoup(open(fname), 'lxml')


def db_save(db_or_el, fname: str):
    """ Persist DB on disk """
    imgs = _db_or_elems(db_or_el)
    return open(fname, 'w').write(DB_TMPL.format('\n'.join(str(el) for el in imgs)))


def db_query(db: BeautifulSoup, c=g_config):
    """ Interactive query and call commands """
    log.info(f'There are {len(db.find_all("img")):,} imgs in img-DB')
    metas, imgs = db_filter(db, c)  # noqa: F8
    from IPython import embed
    embed(colors='linux', confirm_exit=False)


def db_rescue(fname1: str, fname2: str):
    """
    Rescue images from a broken DB. This is pretty slow, so it's not enabled automatically.
    """
    imgs = {}
    for line in open(fname1):
        if not (line and 'img' in line):
            continue
        try:
            soup = BeautifulSoup(line, 'lxml')
            if soup.img:
                for el in soup.find_all('img'):
                    imgs[el['id']] = el
        except Exception as err:
            print('ERR:', err)
    log.info(f'Rescued {len(imgs):,} uniq imgs')
    db_save(tuple(imgs.values()), fname2)


def db_rem_elem(db_or_el, query: str):
    """
    Remove ALL images that match query. The DB is not saved on disk.
    """
    expr = parse_query_expr(query)
    i = 0
    for el in _db_or_elems(db_or_el):
        for prop, func, val in expr:
            ok = []
            m = el_to_meta(el, False)
            if func(m.get(prop), val):
                ok.append(True)
            if ok and all(ok):
                el.decompose()
                i += 1
    log.info(f'{i} imgs removed from DB')
    return i


def db_rem_attr(db_or_el, attr: str):
    """
    Remove the ATTR from ALL images. The DB is not saved on disk.
    """
    i = 0
    for el in _db_or_elems(db_or_el):
        if el.attrs.get(f'data-{attr}'):
            del el.attrs[f'data-{attr}']
            i += 1
    log.info(f'{i} attrs removed from DB')
    return i


def db_check_pth(db_or_el, action=None):
    """ Check all paths from DB (and optionally run an action) """
    i = 0
    for el in _db_or_elems(db_or_el):
        pth = el.attrs['data-pth']
        if not os.path.isfile(pth):
            log.warn(f'Path {pth} is broken')
            i += 1
            if action:
                action(el)
    if i:
        log.warn(f'{i:,} paths are broken')
    else:
        log.info('All paths are working')
    return i


def db_dupes_by(db_or_el, by_attr: str, uid='id'):
    """ Find duplicates by dhash, bhash, etc. """
    dupes: Dict[str, list] = {}
    for el in _db_or_elems(db_or_el):
        if el.attrs.get(f'data-{by_attr}'):
            v = el.attrs[f'data-{by_attr}']
            dupes.setdefault(v, []).append(el.attrs[uid])
    # remove non-dupes from result
    for v in list(dupes):
        if len(dupes[v]) < 2:
            del dupes[v]
    log.info(f'There are {len(dupes):,} duplicates by "{by_attr}"')
    return dupes


def db_filter(db: BeautifulSoup, c=g_config) -> tuple:
    to_native = bool(c.links)
    metas = []
    imgs = []
    for el in db.find_all('img'):
        ext = os.path.splitext(el.attrs['data-pth'])[1]
        if c.exts and ext.lower() not in c.exts:
            continue
        m = el_to_meta(el, to_native)
        if c.filtr:
            ok = []
            for prop, func, val in c.filtr:
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
        if c.limit and c.limit > 0 and len(imgs) >= c.limit:
            break
    if imgs:
        log.info(f'There are {len(imgs):,} filtered imgs')
    return metas, imgs


def db_merge(*args) -> str:
    """ Merge more DBs """
    if len(args) < 2:
        raise Exception(f'DB merge: invalid number of args: {len(args)}')
    log.debug(f'Merging {len(args)} DBs...')

    images: Dict[str, Any] = {}
    for new_content in args:
        for new_img in _db_or_elems(new_content):
            img_id = new_img['id']
            if img_id in images:
                # the logic is to assume the second content is newer,
                # so it contains fresh & better information
                old_img = images[img_id]
                for k in sorted(new_img.attrs):
                    old_img[k] = new_img.attrs[k]
            else:
                images[img_id] = new_img

    elems = []
    for el in sorted(images.values(),
                     reverse=True,
                     key=lambda el: el.attrs.get('data-date', '00' + el['id'])):
        elems.append(str(el))
    log.info(f'Compacted {len(elems):,} imgs')
    return DB_TMPL.format('\n'.join(elems))


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
        **{algo: attr.ib(default=0) for algo in VHASHES},
        **{f'dupe_{algo}': attr.ib(default={}) for algo in VHASHES},
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
                dupes = getattr(stat, f'dupe_{algo}')
                h = el.attrs[f'data-{algo}']
                dupes[h] = dupes.get(h, 0) + 1

    # drop small dupe-v-hash values
    for algo in VHASHES:
        dupes = getattr(stat, f'dupe_{algo}')
        for h in list(dupes):
            if dupes[h] < 2:
                del dupes[h]

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
