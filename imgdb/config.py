from .log import log
from .util import parse_query_expr

from attrs import define, field, validators
from pathlib import Path
from typing import Any, List, Optional
import logging
import re

EXTRA_META = {
    'aperture': (
        'Composite:Aperture',
        'EXIF:FNumber',
        'EXIF:ApertureValue',
    ),
    'shutter-speed': (
        'Composite:ShutterSpeed',
        'EXIF:ExposureTime',
        'EXIF:ShutterSpeedValue',
    ),
    'iso': ('EXIF:ISO', ),
    # 'make': ('EXIF:Make', ),
    # 'model': ('EXIF:Model', ),
    'lens-make': ('EXIF:LensMake', ),
    'lens-model': (
        'Composite:LensID',
        'EXIF:LensModel',
    ),
    # 'orientation': ('EXIF:Orientation', ),
    'rating': (
        'XMP:Rating',
        'Rating',
    ),
    'label': ('XMP:Label', ),
    'keywords': ('IPTC:Keywords', ),
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
    'make-model',
    'top-colors',
]
IMG_ATTRS_LI.extend(IMG_ATTRS_BASE)
IMG_ATTRS_LI.extend(EXTRA_META.keys())


def get_attr_type(attr):
    """ Common helper to get the type of a attr/prop """
    if attr in ('width', 'height', 'bytes', 'iso'):
        return int
    if attr in ('aperture', 'shutter-speed'):
        return float
    return str


IMG_ATTR_TYPES = {n: get_attr_type(n) for n in IMG_ATTRS_LI}


def path_or_none(v: Optional[str]) -> Optional[Path]:
    return Path(v) if v is not None else None


def smart_split(s: Any):
    if isinstance(s, (list, tuple)):
        return s
    if isinstance(s, str):
        return [f'{x.lower()}' for x in re.split('[,; ]', s) if x]
    raise Exception(f'Smart-split: invalid type: {type(s)}!')


def config_parse_q(q: str) -> List[Any]:
    return parse_query_expr(q, IMG_ATTR_TYPES)


@define(kw_only=True)
class Config:
    """
    Config flags from config files and CLI. Used by many functions.
    """

    # database file name
    dbname: str = field(default='imgdb.htm')
    # DON'T CHANGE! this is the DB instance
    # db = field(init=False, repr=False)

    # add input and output
    inputs: List[Path] = field(default=[])
    archive: Path = field(default=None)

    # links pattern
    links: str = field(default='')
    # gallery pattern
    gallery: str = field(default='')
    # gallery wrap at
    wrap_at: int = field(default=1000, validator=validators.ge(10))

    # limit operations to nr of files
    limit: int = field(default=0, validator=validators.ge(0))
    # filter by extension, eg: JPG, PNG, etc
    exts: List[str] = field(default='', converter=smart_split)
    # only files that match a RE pattern
    pmatch: str = field(default='')
    # custom filter for some operations
    filtr: List[Any] = field(default='', converter=config_parse_q)
    # ignore images smaller than (bytes)
    ignore_sz: int = field(default=96)

    # the UID is used to calculate the uniqueness of the img
    # it's possible to limit the size: --uid '{sha256:.8s}'
    # BE VERY CAREFUL !! you can overwrite and LOSE all your images
    # TODO ? validate && sanitize ?
    uid: str = field(default='{blake2b}')

    # extra metadata (shutter-speed, aperture, iso, orientation, etc)
    metadata: List[str] = field(default='', converter=smart_split)

    # one of the operations: copy, move, link
    add_operation: str = field(default='', validator=validators.in_(['', 'copy', 'move', 'link']))
    # DON'T CHANGE! depends on operation
    add_func = field(default=None, init=False, repr=False)

    # cryptographical hashes and perceptual hashes
    # content hashing (eg: BLAKE2b, SHA256, etc)
    hashes: List[str] = field(default='blake2b', converter=smart_split)
    # perceptual hashing (eg: ahash, dhash, vhash, phash)
    v_hashes: List[str] = field(default='dhash', converter=smart_split)

    # DB thumb size, quality and type
    thumb_sz: int = field(default=96, validator=validators.ge(8))
    thumb_qual: int = field(default=70, validator=validators.ge(10))
    thumb_type: str = field(default='webp', validator=validators.in_(['webp', 'jpeg', 'png']))

    # use sym-links instead of hard-links
    sym_links = field(default=False)

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
    verbose: bool = field(default=False)

    # ----- extra options

    # the visual hash image size; a bigger number generates a longer hash;
    visual_hash_size: int = field(default=8, validator=validators.ge(2))

    # the base used to convert visual hash numbers into strings
    # a bigger number generates shorter hashes, but harder to read
    visual_hash_base: int = field(default=32, validator=validators.ge(16))

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
        if self.verbose:
            log.setLevel(logging.DEBUG)
        elif self.silent:
            log.setLevel(logging.ERROR)
        else:
            log.setLevel(logging.INFO)


# Global Config object
g_config = Config()
