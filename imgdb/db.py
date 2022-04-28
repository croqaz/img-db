from .chart import Bar
from .config import g_config
from .img import el_to_meta
from .log import log
from .util import parse_query_expr, hamming_distance
from .vhash import VHASHES

from bs4 import BeautifulSoup
from collections import Counter
from datetime import datetime
from glob import glob
from texttable import Texttable
from typing import Dict, List, Any, Union
import attr
import os.path

DB_TMPL = '<!DOCTYPE html><html lang="en">\n<head><meta charset="utf-8">' + \
          '<title>img-DB</title></head>\n<body>\n{}\n</body></html>'

func_ident = lambda el: el
func_noop = lambda _: None
func_true = lambda _: True


def _db_or_elems(x) -> Union[list, tuple]:
    if isinstance(x, BeautifulSoup):
        return x.find_all('img')
    elif isinstance(x, (list, tuple)):
        return x
    elif isinstance(x, str):
        return BeautifulSoup(x, 'lxml').find_all('img')
    else:
        raise Exception(f'DB or elem internal error! Invalid param type {type(x)}')


def _id_or_elem(x, db):
    # assume it's an ID as a hash
    if isinstance(x, str) and len(x) > 3:
        return db.find('img', {'id': x})
    # assume it's a meta
    elif isinstance(x, dict) and len(x) > 2:
        return db.find('img', {'id': x['id']})
    else:
        raise Exception(f'ID or elem internal error! Invalid param type {type(x)}')


def db_valid_img(elem) -> bool:
    return len(elem.attrs.get('id', '')) > 3 and len(elem.attrs.get('data-pth', '')) > 3 \
        and elem.attrs.get('data-bytes') and elem.attrs.get('data-format')


def db_open(fname: str) -> BeautifulSoup:
    return BeautifulSoup(open(fname), 'lxml')


def db_save(db_or_el, fname: str, sort_by='date'):
    """ Persist DB on disk """
    # TODO: should probably use a meta tag for create and update, but I tried
    # this will be tricky to do bc data usually comes from db_merge, so it's a list
    imgs = [f'<!-- Updated {datetime.now().strftime("%Y-%m-%dT%H:%M")} -->']
    for el in sorted(_db_or_elems(db_or_el),
                     reverse=True,
                     key=lambda x: x.attrs.get(f'data-{sort_by}', '00' + x['id'])):
        imgs.append(el)
    htm = DB_TMPL.format('\n'.join(str(el) for el in imgs))
    log.debug(f'Saving {len(imgs):,} imgs, disk size {len(htm)//1024:,} KB')
    return open(fname, 'w').write(htm)


def db_debug(db: BeautifulSoup, c=g_config):
    """ Interactive query and call commands """
    log.info(f'There are {len(db.find_all("img")):,} imgs in img-DB')
    metas, imgs = db_filter(db, c)  # noqa: F8
    from IPython import embed
    embed(colors='linux', confirm_exit=False)


def db_rem_elem(db_or_el, query: str) -> int:
    """
    Remove ALL images that match query. The DB is not saved on disk.
    """
    func_match = lambda el: el.decompose() or True
    elems, _ = db_query_map(db_or_el, query, func_match, func_noop)
    log.info(f'{len(elems)} imgs removed from DB')
    return len(elems)


def db_rem_attr(db_or_el, attr: str) -> int:
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


def elem_find_similar(db: BeautifulSoup, uid: str) -> tuple:
    """ Find images similar to elem.
    This also returns the element itself, so you can compare the MAX value. """
    extra = ('aperture', 'bytes', 'date', 'format', 'iso', 'make-mode', 'model', 'shutter-speed')
    similar: Dict[str, Any] = {}
    details: Dict[str, Any] = {}
    el = _id_or_elem(uid, db)
    for other in _db_or_elems(db):
        oid = other['id']
        for h in VHASHES:
            v1 = el.attrs.get(f'data-{h}')
            v2 = other.attrs.get(f'data-{h}')
            if v1 and v2 and v1 == v2:
                similar[oid] = similar.get(oid, 0) + 3
            elif v1 and v2:
                dist = hamming_distance(v1, v2)
                if v1 and v2 and dist < 3:
                    similar[oid] = similar.get(oid, 0) + dist
        if similar.get(oid, 0) >= 3:
            for prop in extra:
                v1 = el.attrs.get(f'data-{prop}')
                v2 = other.attrs.get(f'data-{prop}')
                if v1 and v2 and v1 == v2:
                    similar[oid] = similar.get(oid, 0) + 1
                elif v1 and v2:
                    details.setdefault(oid, {})[prop] = f'{v1} vs {v2}'
        elif similar.get(oid, 10) <= 2:
            del similar[oid]
    log.debug(f'There are {len(similar):,} similar images')
    return similar, details


def db_dupes_by(db_or_el, by_attr: str, uid='id') -> dict:
    """ Find duplicates by one attr: dhash, bhash, etc. """
    dupes: Dict[str, list] = {}  # attr -> list of IDs
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


def db_compare_imgs(db: BeautifulSoup, ids: list):
    table = Texttable()
    table.set_cols_dtype(['t', 't', 't', 't', 't', 'i', 'a', 't', 'i', 'f', 'f'])
    table.set_cols_width([8, 10, 10, 4, 4, 8, 10, 12, 4, 5, 5])
    head = ('id', 'dhash', 'rchash', 'format', 'mode', 'bytes', 'date', 'make-model',
            'iso', 'aperture', 'shutter-speed')
    rows: List[List[str]] = [list(head)]
    rows[0][3] = 'fmt'
    rows[0][-2] = 'apert'
    rows[0][-1] = 'shutt speed'
    for uid in ids:
        row = []
        el = _id_or_elem(uid, db)
        for prop in head:
            if prop == 'id':
                row.append(uid[:8])
            else:
                row.append(el.attrs.get(f'data-{prop}', ''))
        rows.append(row)
    table.add_rows(rows)
    print(table.draw())


def db_filter(db: BeautifulSoup, c=g_config) -> tuple:
    metas = []
    imgs = []
    for el in db.find_all('img'):
        ext = os.path.splitext(el.attrs['data-pth'])[1]
        if c.exts and ext.lower() not in c.exts:
            continue
        m = el_to_meta(el)
        if c.filter:
            ok = []
            for prop, func, val in c.filter:
                ok.append(func(m.get(prop), val))
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


def db_query_map(db_or_el, query, func_match, func_not) -> tuple:
    """
    Helper function to find elems from query and transform them,
    to generate 2 lists of matching/not-matching elements.
    """
    expr = parse_query_expr(query)
    elems1, elems2 = [], []
    for el in _db_or_elems(db_or_el):
        m = el_to_meta(el)
        ok = [func(m.get(prop), val) for prop, func, val in expr]
        if ok and all(ok):
            r = func_match(el)
            if r is not None:
                elems1.append(r)
        else:
            r = func_not(el)
            if r is not None:
                elems2.append(r)
    return elems1, elems2


def db_split(db_or_el, query) -> tuple:
    """ Move matching elements elements into DB1, or DB2 """
    li1, li2 = db_query_map(db_or_el, query, func_ident, func_ident)
    log.info(f'{len(li1)} imgs moved to DB1, {len(li2)} imgs moved to DB1')
    return li1, li2


def db_merge(*args: str) -> tuple:
    """ Merge more DBs """
    if len(args) < 2:
        raise Exception(f'DB merge: invalid number of args: {len(args)}')
    log.debug(f'Will merge {len(args)} DBs...')
    imgs: Dict[str, Any] = {}
    for new_content in args:
        elems = _db_or_elems(new_content)
        log.debug(f'Processing {len(elems)} elems...')
        for new_img in elems:
            img_id = new_img['id']
            if img_id in imgs:
                # the logic is to assume the second content is newer,
                # so it contains fresh & better information
                old_img = imgs[img_id]
                for k in sorted(new_img.attrs):
                    # don't keep blank values
                    val = new_img.attrs[k].strip()
                    if not val:
                        continue
                    old_img[k] = new_img.attrs[k]
            else:
                imgs[img_id] = new_img
    return tuple(imgs.values())


def db_rescue(fname: str) -> tuple:
    """
    Rescue images from a possibly broken DB.
    This is pretty slow, so it's not enabled on save.
    """
    imgs = {}
    for line in open(fname):
        if not (line and 'img' in line):
            continue
        try:
            for el in _db_or_elems(line):
                if db_valid_img(el):
                    imgs[el['id']] = el
        except Exception as err:
            log.warning(err)
    log.info(f'Rescued {len(imgs):,} unique imgs')
    return tuple(imgs.values())


def db_sync_arch(db_or_el, archive):
    """ Sync from archive to DB.
    The archive is the source of truth and it must be in perfect sync
    with the DB. This function makes sure the files from DB and arch are the same.
    """
    broken = []
    working = []
    for el in _db_or_elems(db_or_el):
        pth = el.attrs['data-pth']
        if os.path.isfile(pth):
            working.append(pth)
        else:
            log.warn(f'Path {pth} is broken')
            broken.append(el)
    if broken:
        log.warn(f'{len(broken):,} DB paths are broken')
        resp = input('Do you want to remove them from DB? y/n ')
        if resp.strip() == 'y':
            for el in broken:
                el.decompose()
        else:
            log.info('Skipping')
    else:
        log.info('All DB paths are working')

    not_imported = []
    index = 0
    for pth in sorted(glob(f'{archive.rstrip("/")}/**/*.*')):
        if pth not in working:
            log.warn(f'Path {pth} is not imported')
            not_imported.append(pth)
        else:
            index += 1
    if not_imported:
        log.warn(f'{len(not_imported):,} files are not imported')
    else:
        log.info(f'All {index:,} archive files are imported')


def db_doctor(c=g_config):
    """ Working day and night to make you better 👩🏻‍⚕️👨🏻‍⚕️💉 """
    elems = db_rescue(c.dbname)
    db = _db_or_elems(elems)
    db_sync_arch(db, c.archive)
    db_save([el for el in db if el.name], c.dbname)


DbStats = attr.make_class(
    'DbStats', attrs={
        # coverage values
        'total': attr.ib(default=0),
        'bytes': attr.ib(default=0),
        'format': attr.ib(default=0),
        'mode': attr.ib(default=0),
        'size': attr.ib(default=0),
        'width': attr.ib(default=0),
        'height': attr.ib(default=0),
        'date': attr.ib(default=0),
        'm_model': attr.ib(default=0),
        's_speed': attr.ib(default=0),
        'aperture': attr.ib(default=0),
        'iso': attr.ib(default=0),
        **{algo: attr.ib(default=0) for algo in VHASHES},
        # count uniq values
        'exts_c': attr.ib(default=None),
        'mode_c': attr.ib(default=None),
        'format_c': attr.ib(default=None),
    })


def _db_stats_repr(self: Any) -> str:
    table = Texttable()
    table.set_cols_dtype(['t', 't', 'i'])
    HEAD = ('bytes', 'size', 'format', 'mode', 'date', 'm_model', 'iso', 'aperture', 's_speed')
    for prop in HEAD:
        table.add_row([prop, f'{(getattr(self, prop) / self.total * 100):.2f}%', getattr(self, prop)])
    for algo in VHASHES:
        table.add_row([algo, f'{(getattr(self, algo) / self.total * 100):.2f}%', getattr(self, algo)])
    report: str = table.draw() + '\n'  # type: ignore
    del table
    report += ('\nEXTS details:' + Bar(self.exts_c).render())
    report += ('\nFORMAT details:' + Bar(self.format_c).render())
    report += ('\nMODE details:' + Bar(self.mode_c).render())
    return report


DbStats.__repr__ = _db_stats_repr  # type: ignore


def db_stats(db: BeautifulSoup):
    stat = DbStats()
    values: Dict[str, list] = {
        'exts': [],
        'format': [],
        'mode': [],
        'model': [],
        'bytes': [],
        'width': [],
        'height': [],
    }
    for el in db.find_all('img'):
        stat.total += 1
        ext = os.path.splitext(el.attrs['data-pth'])[1]
        values['exts'].append(ext.lower())

        m = el_to_meta(el)
        if m.get('date'):
            stat.date += 1
        if m.get('iso'):
            stat.iso += 1
        if m.get('make-model'):
            stat.m_model += 1
            # values['model'].append(m['make-model'].lower())
        if m.get('shutter-speed'):
            stat.s_speed += 1
        if m.get('aperture'):
            stat.aperture += 1
        if m.get('iso'):
            stat.iso += 1
        if m.get('format'):
            stat.format += 1
            values['format'].append(m['format'])
        if m.get('mode'):
            stat.mode += 1
            values['mode'].append(m['mode'])
        if m.get('bytes'):
            stat.bytes += 1
            # values['bytes'].append((m['bytes'])
        if el.attrs.get('size'):
            stat.size += 1
        if m.get('width'):
            stat.width += 1
            values['width'].append(m['width'])
        if m.get('height'):
            stat.height += 1
            values['height'].append(m['height'])
        for algo in VHASHES:
            if m.get(f'{algo}'):
                setattr(stat, algo, getattr(stat, algo) + 1)

    stat.exts_c = dict(Counter(values['exts']).most_common(10))
    stat.format_c = dict(Counter(values['format']).most_common(10))
    stat.mode_c = dict(Counter(values['mode']).most_common(10))
    return stat, values
