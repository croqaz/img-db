# the visual hash img size
VISUAL_HASH_SIZE = 8

# the base used to convert visual hash numbers into strings
VISUAL_HASH_BASE = 32

# cryptographic result size
HASH_DIGEST_SIZE = 24

# how many colors per channel, when calculating top colors
CLR_CHAN = 5

IMG_DATE_FMT = '%Y-%m-%d %H:%M:%S'
MAKE_MODEL_FMT = '{make}-{model}'

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

IMG_ATTRS = [
    'pth',
    'format',
    'mode',
    'width',
    'height',
    'bytes',
    'date',
    'make-model',
]
IMG_ATTRS.extend(EXTRA_META.keys())
