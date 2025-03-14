import hashlib
import json
import logging
import os
import re
import shutil
from os.path import expanduser, isfile
from pathlib import Path
from typing import Any

from attrs import define, field, validators

from .algorithm import ALGORITHMS
from .log import log
from .util import parse_query_expr
from .vhash import VHASHES

EXTRA_META = {
    'aperture': True,
    'focal-length': True,
    'iso': True,
    'lens-maker-model': True,
    'shutter-speed': True,
    # TODO ...
    # 'orientation': ('EXIF:Orientation', ),
    'rating': (
        'XMP:Rating',
        'Rating',
    ),
    'label': ('XMP:Label',),
    'keywords': ('IPTC:Keywords',),
    'headline': (
        'IPTC:Headline',
        'XMP:Headline',
    ),
    'caption': (
        'IPTC:Caption-Abstract',
        'XMP:Description',
    ),
}

# MANDATORY attributes
IMG_ATTRS_BASE = [
    'pth',
    'format',
    'mode',
    'bytes',
]
# important attributes
IMG_ATTRS_LI = [
    'width',
    'height',
    'date',
    'maker-model',
    'top-colors',
]
IMG_ATTRS_LI.extend(IMG_ATTRS_BASE)
IMG_ATTRS_LI.extend(EXTRA_META.keys())

IMG_DATE_FMT = '%Y-%m-%d %H:%M:%S'


def get_attr_type(attr):
    """Common helper to get the type of a attr/prop"""
    if attr in ('width', 'height', 'bytes', 'focal-length', 'iso'):
        return int
    if attr in ('aperture', 'shutter-speed'):
        return float
    return str


IMG_ATTR_TYPES = {n: get_attr_type(n) for n in IMG_ATTRS_LI}


def path_or_none(v: str | None) -> Path | None:
    return Path(v) if v is not None else None


def smart_split(s: Any):
    if isinstance(s, (list, tuple)):
        return s
    if isinstance(s, str):
        return [f'{x.lower()}' for x in re.split('[,; ]', s) if x]
    raise Exception(f'Smart-split: invalid type: {type(s)}!')


def split_exts(s: str) -> list[str]:
    return [f'.{e.lstrip(".").lower()}' for e in re.split('[,; ]', s) if e]


def config_parse_q(q: str) -> list[Any]:
    return parse_query_expr(q, IMG_ATTR_TYPES)


def validate_c_hashes(cls, attribute, values):
    allowed = sorted(hashlib.algorithms_available)
    assert all(v in allowed for v in values), f'Crypto hashes must be in: {allowed}'


def convert_v_hashes(s: Any) -> list[str]:
    return list(VHASHES) if s == '*' else smart_split(s)


def validate_v_hashes(cls, attribute, values):
    allowed = sorted(VHASHES)
    assert all(v in VHASHES for v in values), f'Visual hashes must be in: {allowed}'


JSON_SAFE = (
    'algorithms',
    'deep',
    'exts',
    'metadata',
    'shuffle',
    'sym_links',
    'thumb_qual',
    'thumb_sz',
    'thumb_type',
    'top_color_cut',
    'c_hashes',
    'v_hashes',
    'wrap_at',
)


@define(kw_only=True)
class Config:
    """Config flags from config files and CLI. Used by many functions."""

    # simulate/ dry-run ?
    dry_run: bool = field(default=False)
    # database file name
    dbname: str = field(default='imgdb.htm')
    # general export format
    format: str = field(default='')

    # output folder
    output: Path = field(default=None)
    # archive subfolders using first chr from new name
    archive_subfolder_len: int = field(default=1, validator=validators.and_(validators.ge(0), validators.le(4)))

    # links pattern
    links: str = field(default='')
    # gallery pattern
    gallery: str = field(default='')
    # add or remove attrs from imgs in gallery
    add_attrs: str = field(default='', converter=smart_split)
    del_attrs: str = field(default='', converter=smart_split)
    # gallery wrap at
    wrap_at: int = field(default=1000, validator=validators.ge(100))
    # gallery custom template file
    tmpl: str = field(default='img_gallery.html')

    # limit operations to nr of files
    limit: int = field(default=0, validator=validators.ge(0))
    # filter by extension, eg: JPG, PNG, etc
    exts: list[str] = field(default='', converter=split_exts)
    # custom filter for some operations
    filter: list[Any] = field(default='', converter=config_parse_q)

    # the UID is used to calculate the uniqueness of the img
    # it's possible to limit the size: --uid '{sha256:.8s}'
    # BE VERY CAREFUL !! you can overwrite and LOSE all your images
    # TODO ? validate && sanitize ?
    uid: str = field(default='{blake2b}')

    # extra metadata (shutter-speed, aperture, iso, orientation, etc)
    metadata: list[str] = field(default='', converter=smart_split)
    # extra algorithms to run (top colors, average color, AI detect objects and people)
    algorithms: list[str] = field(default='', converter=smart_split)

    # one of the operations: copy, move, link
    operation: str = field(default='', validator=validators.in_(['', 'copy', 'move', 'link']))
    # DON'T CHANGE! depends on operation
    add_func = field(default=None, init=False, repr=False)

    # cryptographical hashes and perceptual hashes
    # content hashing (eg: BLAKE2b, SHA256, etc)
    c_hashes: list[str] = field(default='blake2b', converter=smart_split, validator=validate_c_hashes)
    # perceptual hashing (eg: ahash, dhash, vhash, phash)
    v_hashes: list[str] = field(default='dhash', converter=convert_v_hashes, validator=validate_v_hashes)

    # DB thumb size, quality and type
    thumb_sz: int = field(default=128, validator=validators.and_(validators.ge(16), validators.le(512)))
    thumb_qual: int = field(default=70, validator=validators.and_(validators.ge(25), validators.le(99)))
    thumb_type: str = field(default='webp', validator=validators.in_(['webp', 'jpeg', 'png']))

    # use sym-links instead of hard-links
    sym_links: bool = field(default=False)

    # option to skip imgs imported in DB
    skip_imported: bool = field(default=False)
    # deep search of imgs
    deep: bool = field(default=False)
    # don't force it - get a bigger hammer
    force: bool = field(default=False)
    # randomize before limiting
    shuffle: bool = field(default=False)
    # enable / disable logs
    silent: bool = field(default=False)
    verbose: bool = field(default=True)

    # ----- extra options

    # cryptographic hash result size
    hash_digest_size: int = field(default=24, validator=validators.ge(6))

    # how many colors per channel, when calculating top colors
    top_color_channels: int = field(default=5, converter=int, validator=validators.ge(1))
    # DON'T CHANGE! depends on top color channels; closest value to round to
    top_clr_round_to = field(init=False, repr=False)

    # ignore top colors below threshold percent
    top_color_cut: int = 25

    def __attrs_post_init__(self):
        self.top_clr_round_to = round(255 / self.top_color_channels)
        if self.dbname:
            self.dbname = expanduser(self.dbname)
        if self.metadata == ['*']:
            self.metadata = sorted(EXTRA_META)
        if self.algorithms == ['*']:
            self.algorithms = list(ALGORITHMS)
        if self.operation == 'move':
            self.add_func = shutil.move
        elif self.operation == 'copy':
            self.add_func = shutil.copy2
        elif self.operation == 'link':
            self.add_func = os.link
        if self.verbose:
            log.setLevel(logging.DEBUG)
        elif self.silent:
            log.setLevel(logging.ERROR)
        else:
            log.setLevel(logging.INFO)

    @classmethod
    def from_file(
        cls,
        fname: str,
        initial: dict | None = None,
        extra: dict | None = None,
    ) -> 'Config':
        cfg = initial if initial else {}
        if fname:
            if not isfile(fname):
                raise ValueError("Config file doesn't exist!")
            if fname.endswith('.json'):
                with open(fname) as fd:
                    cfg = json.load(fd)
                    log.debug(f'loaded Config: {cfg}')
            else:
                raise ValueError('Invalid config type! Only JSON is supported!')
            for k in cfg:
                if k not in JSON_SAFE:
                    raise ValueError(f'Invalid config property: "{k}"')
        if extra:
            for key, val in extra.items():
                cfg[key] = val
        return cls(**cfg)


# Global Config object
g_config = Config()
