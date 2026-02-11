import csv
import json
import os
import os.path
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import attr
from bs4 import BeautifulSoup
from bs4.element import Tag
from texttable import Texttable

from imgdb.fsys import find_files

from .chart import Bar
from .config import g_config
from .img import el_to_meta
from .log import log
from .util import parse_query_expr
from .vhash import VHASHES

DB_HEAD = """
<head>
<meta charset="utf-8">
<meta name="robots" content="noindex, nofollow">
<meta name="application-name" content="img-DB">
<meta name="generator" content="img-DB v0.3">
</head>
""".strip()

DB_TMPL = """
<!DOCTYPE html><html lang="en">
{}
<body>\n{}\n</body></html>
""".strip()

func_ident = lambda el: el
func_noop = lambda _: None


def _db_or_elems(x) -> list | tuple:  # pragma: no cover
    if isinstance(x, ImgDB):
        return x.images
    elif isinstance(x, BeautifulSoup):
        return x.find_all('img')
    elif isinstance(x, (list, tuple)):
        return x
    elif isinstance(x, str):
        return BeautifulSoup(x, 'lxml').find_all('img')
    else:
        raise Exception(f'DB or elem internal error! Invalid param type {type(x)}')


def _is_valid_img(elem) -> bool:
    return (
        len(elem.attrs.get('id', '')) > 3
        and len(elem.attrs.get('data-pth', '')) > 3
        and elem.attrs.get('data-bytes')
        and elem.attrs.get('data-mode')
        and elem.attrs.get('data-format')
    )


class ImgDB:
    """Database class for managing image metadata stored in HTML format."""

    def __init__(self, fname: Optional[str] = None, elems: Optional[list | tuple] = None, config=None):
        """
        Initialize the DB from a file.
        """
        if not (fname or elems or config):
            raise Exception('DB init error: either fname, elems, or config must be provided')
        self.config = config or g_config
        self.fname = fname or self.config.dbname
        if elems:
            # In case of elems, we lose all the head meta info
            html = DB_TMPL.format(DB_HEAD, '\n'.join(str(el) for el in elems))
            self.db = BeautifulSoup(html, 'lxml')
        else:
            self.db = BeautifulSoup(open(self.fname, 'rb'), 'lxml')  # NOQA

        for elem in self.db.find_all('img'):
            if not _is_valid_img(elem):
                log.warning(f'Invalid img found in DB will be removed: {str(elem)[:80]}...')
                elem.decompose()

        if not (self.db.head and self.db.head.meta):
            self.db.head = BeautifulSoup(DB_HEAD, 'lxml').head  # type: ignore

        # create date-created meta tag
        date_now = datetime.now().strftime('%Y-%m-%dT%H:%M')
        date_created = self.db.head.find_all('meta', attrs={'name': 'date-created'})  # type: ignore
        if not date_created:
            self.db.head.append(self.db.new_tag('meta', attrs={'name': 'date-created', 'content': date_now}))  # type: ignore

        self.meta: dict[str, Any] = {}
        for meta in self.db.head.find_all('meta', attrs={'name': True, 'content': True}):  # type: ignore
            self.meta[meta.attrs['name']] = meta.attrs['content']  # type: ignore

    @property
    def images(self) -> list:
        """Return all image elements in the DB."""
        return self.db.find_all('img')

    def __len__(self) -> int:
        """Return the number of images in the DB."""
        return len(self.images)

    def save(self, fname: Optional[Path | str] = None, sort_by='date'):
        """Persist DB on disk."""
        if fname is None:
            fname = self.fname
        if not (self.db.head and self.db.head.meta):
            self.db.head = BeautifulSoup(DB_HEAD, 'lxml').head  # type: ignore

        # update date-updated meta tag
        date_now = datetime.now().strftime('%Y-%m-%dT%H:%M')
        date_updated = self.db.head.find_all('meta', attrs={'name': 'date-updated'})  # type: ignore
        if date_updated:
            date_updated[0]['content'] = date_now
        else:
            self.db.head.append(self.db.new_tag('meta', attrs={'name': 'date-updated', 'content': date_now}))  # type: ignore

        imgs = sorted(set(self.images), reverse=True, key=lambda x: x.attrs.get(f'data-{sort_by}', '00' + x['id']))
        html = DB_TMPL.format(self.db.head.prettify().strip(), '\n'.join(str(el) for el in imgs))
        self.db = BeautifulSoup(html, 'lxml')
        log.debug(f'Saving {(len(imgs)):,} imgs, disk size {len(html) // 1024:,} KB')
        return open(fname, 'w').write(html)

    def filter(self, query: Optional[str] = None, native=True) -> tuple[list, list]:
        """Filter images based on config settings."""
        expr = None
        if query:  # NOQA
            expr = parse_query_expr(query)
        elif self.config.filter:
            expr = parse_query_expr(self.config.filter)
        metas = []
        imgs = []
        for el in self.images:
            ext = os.path.splitext(el.attrs['data-pth'])[1]
            if self.config.exts and ext.lower() not in self.config.exts:
                continue
            m = el_to_meta(el, native)
            if expr:
                ok = []
                for prop, func, val in expr:
                    ok.append(func(m.get(prop), val))
                if ok and all(ok):
                    metas.append(m)
                    imgs.append(el)
            else:
                metas.append(m)
                imgs.append(el)
            if self.config.limit and self.config.limit > 0 and len(imgs) >= self.config.limit:
                break
        if imgs:
            log.info(f'There are {len(imgs):,} filtered imgs')
        else:
            log.info("The filter didn't match any image!")
        return metas, imgs

    def rem_elem(self, query: str) -> int:
        """
        Remove ALL images that match query. The DB is not saved on disk.
        """
        expr = parse_query_expr(query)
        i = 0
        for el in self.images:
            m = el_to_meta(el)
            ok = [func(m.get(prop), val) for prop, func, val in expr]
            if ok and all(ok):
                el.decompose()
                i += 1
        log.info(f'{i} images matching "{query}" removed from DB')
        return i

    def rem_attr(self, attr: str) -> int:
        """
        Remove the ATTR from ALL images. The DB is not saved on disk.
        """
        i = 0
        a = 0
        for el in self.images:
            i += 1
            if el.attrs.get(f'data-{attr}'):
                del el.attrs[f'data-{attr}']
                a += 1
        log.info(f'{a} attrs removed from {i} imgs in DB')
        return i

    def query_map(self, query, func_match, func_not) -> tuple[list, list]:
        """
        Helper function to find elems from query and transform them,
        to generate 2 lists of matching/ not-matching mapped elems.
        """
        expr = parse_query_expr(query)
        matching, not_matching = [], []
        for el in self.images:
            m = el_to_meta(el)
            ok = [func(m.get(prop), val) for prop, func, val in expr]
            if ok and all(ok):
                r = func_match(el)
                if r is not None:
                    matching.append(r)
            else:
                r = func_not(el)
                if r is not None:
                    not_matching.append(r)
        return matching, not_matching

    def sync_folders(self, folders: list[str]) -> tuple[int, int, int]:
        """
        Sync from a list of folders, to DB.
        The folders are the source of truth and must be in perfect sync with the DB,
        any extra files in DB will be removed.
        This function makes sure the files from DB and folders are the same, in one
        direction ( from folders to DB ).
        If there are extra files in the folders, they should be imported separately.
        """
        broken = []
        working = []
        for el in self.images:
            pth = el.attrs['data-pth']
            if os.path.isfile(pth):
                working.append(pth)
            else:
                log.warning(f'Path {pth} is broken')
                broken.append(el)
        if broken:
            log.warning(f'{len(broken):,} DB paths are broken and will be purged from DB')
            for el in broken:
                el.decompose()
        else:
            log.info('All DB paths are working')

        not_imported = []
        index = 0
        for pth in find_files([Path(f) for f in folders], self.config):
            if pth not in working:
                log.warning(f'Path {pth} is not imported')
                not_imported.append(pth)
            else:
                index += 1
        if not_imported:
            log.warning(f'{len(not_imported):,} files are not imported')
        else:
            log.info(f'All {index:,} archive files are imported')
        return len(working), len(broken), len(not_imported)

    def export(self, fname: Optional[Path | str] = None):
        """Export filtered metadata to various formats."""
        metas, _ = self.filter()
        format = self.config.format.lower()
        if fname:  # NOQA
            fd = open(fname, 'w', newline='')  # NOQA
        else:
            fd = sys.__stdout__
        if format == 'json':
            fd.write(json.dumps(metas, ensure_ascii=False, indent=2))
        elif format == 'jl':
            for m in metas:
                fd.write(json.dumps(m, ensure_ascii=False))
        elif format in ('csv', 'html', 'table'):
            h = {'id'}
            for m in metas:
                h = h.union(m.keys())
            if not h:
                return
            h.remove('id')  # remove them here to have them first, in order
            h.remove('pth')
            header = ['id', 'pth'] + sorted(h)
            del h
            if format == 'csv':
                writer = csv.writer(fd, quoting=csv.QUOTE_NONNUMERIC)
                writer.writerow(header)
                for m in metas:
                    writer.writerow([m.get(h, '') for h in header])
            else:
                fd.write('<table style="font-family:mono">\n')
                fd.write('<tr>' + ''.join(f'<td>{h}</td>' for h in header) + '</tr>\n')
                for m in metas:
                    fd.write('<tr>' + ''.join(f'<td>{m.get(h, "")}</td>' for h in header) + '</tr>\n')
                fd.write('</table>\n')
        else:
            raise ValueError(f'Invalid export format: {format}!')

    def stats(self):  # pragma: no cover
        """Calculate database statistics."""
        stat = DbStats()
        values: dict[str, list] = {
            'exts': [],
            'format': [],
            'mode': [],
            'model': [],
            'bytes': [],
            'width': [],
            'height': [],
        }
        for el in self.images:
            stat.total += 1
            ext = os.path.splitext(el.attrs['data-pth'])[1]
            values['exts'].append(ext.lower())

            m = el_to_meta(el, native=False)
            if m.get('date'):
                stat.date += 1
            if m.get('iso'):
                stat.iso += 1
            if m.get('maker-model'):
                stat.m_m += 1
                values['model'].append(m['maker-model'])
            if m.get('shutter-speed'):
                stat.s_speed += 1
            if m.get('focal-length'):
                stat.f_length += 1
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
        return stat

    def debug(self):  # pragma: no cover
        """
        Interactive query and call commands.
        """
        log.info(f'There are {len(self):,} imgs in {self.fname} DB')
        metas, imgs = self.filter()
        from IPython import embed

        embed(colors='linux', confirm_exit=False)


def db_split(self, query) -> tuple[list, list]:
    """
    Split matching elements by query, into lists of elems.
    The first value is the list of matching elems,
    the second value is the list of non-matching elems.
    """
    matching, not_matching = self.query_map(query, func_ident, func_ident)
    log.info(f'{len(matching)} imgs are matching, {len(not_matching)} imgs are not matching')
    return matching, not_matching


def db_merge(*args: Any) -> tuple[Tag, ...]:
    """Merge the image elements from more DBs."""
    if len(args) < 2:
        raise Exception(f'DB merge: invalid number of args: {len(args)}')
    log.debug(f'Will merge {len(args)} DBs...')
    imgs: dict[str, Any] = {}
    for new_content in args:
        elems = _db_or_elems(new_content)
        log.debug(f'Processing {len(elems)} DB elems...')
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


DbStats = attr.make_class(  # pragma: no cover
    'DbStats',
    attrs={  # pragma: no cover
        # coverage values
        'total': attr.ib(default=0),
        'bytes': attr.ib(default=0),
        'format': attr.ib(default=0),
        'mode': attr.ib(default=0),
        'size': attr.ib(default=0),
        'width': attr.ib(default=0),
        'height': attr.ib(default=0),
        'date': attr.ib(default=0),
        'm_m': attr.ib(default=0),
        's_speed': attr.ib(default=0),
        'f_length': attr.ib(default=0),
        'aperture': attr.ib(default=0),
        'iso': attr.ib(default=0),
        **{algo: attr.ib(default=0) for algo in VHASHES},
        # count uniq values
        'exts_c': attr.ib(default=None),
        'mode_c': attr.ib(default=None),
        'format_c': attr.ib(default=None),
    },
)


def _db_stats_repr(self: Any) -> str:  # pragma: no cover
    table = Texttable()
    table.set_cols_dtype(['t', 't', 'i'])
    HEAD = ('bytes', 'size', 'format', 'mode', 'date', 'm_m', 'iso', 'aperture', 's_speed')
    for prop in HEAD:
        table.add_row([prop, f'{(getattr(self, prop) / self.total * 100):.2f}%', getattr(self, prop)])
    for algo in VHASHES:
        table.add_row([algo, f'{(getattr(self, algo) / self.total * 100):.2f}%', getattr(self, algo)])
    report: str = table.draw() + '\n'  # type: ignore
    del table
    report += '\nEXTS details:' + Bar(self.exts_c).render()
    report += '\nFORMAT details:' + Bar(self.format_c).render()
    report += '\nMODE details:' + Bar(self.mode_c).render()
    return report


DbStats.__repr__ = _db_stats_repr  # type: ignore
