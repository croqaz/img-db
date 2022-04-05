from .util import parse_query_expr

from attrs import define, field, validators
from pathlib import Path
from typing import Any, List, Optional
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
    'make': ('EXIF:Make', ),
    'model': ('EXIF:Model', ),
    'lens-make': ('EXIF:LensMake', ),
    'lens-model': (
        'Composite:LensID',
        'EXIF:LensModel',
    ),
    'orientation': ('EXIF:Orientation', ),
}

IMG_ATTRS_LI = [
    'pth',
    'format',
    'mode',
    'width',
    'height',
    'bytes',
    'date',
    'make-model',
    'top-colors',
]
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


@define(kw_only=True)
class Config:
    """
    Config flags from config files and CLI. Used by many functions.
    """

    # database file name
    dbname: str = field(default='imgdb.htm')
    # DON'T CHANGE! this is the DB instance
    db = field(init=False, repr=False)

    # add input and output
    input: List[str] = []
    output: str = ''

    # links pattern
    links: str = field(default='')
    # gallery pattern
    gallery: str = field(default='')

    # limit operations to nr of files
    limit: int = field(default=0)
    # filter by extension, eg: JPG, PNG, etc
    exts: List[str] = field(default='', converter=smart_split)
    # only files that match a RE pattern
    pmatch: str = ''
    # custom filter for some operations
    filter: List[str] = field(default='', converter=lambda x: parse_query_expr(x, IMG_ATTR_TYPES))
    # ignore images smaller than (bytes)
    ignore_sz: int = 100

    # how to calculate the uniqueness of the img
    # TODO ? sanitize ?
    uid: str = field(default='{blake2b}')

    # extra metadata (shutter-speed, aperture, iso, orientation, etc)
    metadata: List[str] = field(default='', converter=smart_split)

    # one of the operations: copy, move, link
    add_operation: str = ''
    # DON'T CHANGE! depends on operation
    add_func = field(init=False, repr=False)

    # cryptographical hashes and perceptual hashes
    hashes: List[str] = field(default='blake2b', converter=smart_split)
    v_hashes: List[str] = field(default='dhash', converter=smart_split)

    thumb_sz: int = 100
    thumb_qual: int = 70
    thumb_type: str = 'webp'

    # use sym-links instead of hard-links
    sym_links = field(default=False)

    force: bool = field(default=False)
    shuffle: bool = field(default=False)
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
    top_color_channels: int = field(default=5,  converter=int, validator=validators.ge(1))
    # DON'T CHANGE! depends on top color channels; closest value to round to
    top_clr_round_to = field(init=False, repr=False)

    # ignore top colors below threshold percent
    top_color_cut: int = 25

    def __attrs_post_init__(self):
        self.top_clr_round_to = round(255 / self.top_color_channels)
        # operation = shutil.move
        # operation = shutil.copy2
        # operation = os.link
        self.add_func = ...


# Global Config object
g_config = Config()
