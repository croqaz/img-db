"""
Core EXIF parsing machinery.
Adapted from exif-PY:
https://github.com/ianare/exif-py
MakerNote decoding has been intentionally removed.
"""

import struct
from fractions import Fraction
from pyexpat import ExpatError
from typing import Any, BinaryIO, Callable, Dict, List, Optional, Tuple, Union
from xml.dom.minidom import parseString

from ..log import log as logger
from .tags import (
    DEFAULT_STOP_TAG,
    EXIF_TAGS,
    FIELD_DEFINITIONS,
    FLOAT_FIELD_TYPES,
    IGNORE_TAGS,
    RATIO_FIELD_TYPES,
    SIGNED_FIELD_TYPES,
    FieldType,
    IfdDictValue,
    SubIfdTagDictValue,
)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ExifError(Exception):
    """Base class for all errors."""


class InvalidExif(ExifError):
    """The EXIF is invalid."""


class ExifNotFound(ExifError):
    """The EXIF could not be found."""


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------


def __ord(dta: Union[str, int]) -> int:
    if isinstance(dta, str):
        return ord(dta)
    return dta


def __degrees_to_decimal(degrees: float, minutes: float, seconds: float) -> float:
    """
    Converts coordinates from a degrees minutes seconds format to a decimal degrees format.
    Reference: https://en.wikipedia.org/wiki/Geographic_coordinate_conversion
    """
    return degrees + minutes / 60 + seconds / 3600


def get_gps_coords(tags: dict) -> Optional[Tuple[float, float]]:
    """
    Extract tuple of latitude and longitude values in decimal degrees format from EXIF tags.
    Return None if no GPS coordinates are found.
    Handles regular and serialized Exif tags.
    """
    gps = {
        'lat_coord': 'GPS GPSLatitude',
        'lat_ref': 'GPS GPSLatitudeRef',
        'lng_coord': 'GPS GPSLongitude',
        'lng_ref': 'GPS GPSLongitudeRef',
    }

    # Verify if required keys are a subset of provided tags
    if not set(gps.values()) <= tags.keys():
        return None

    # If tags have not been converted to native Python types, do it
    if not isinstance(tags[gps['lat_coord']], list):
        tags[gps['lat_coord']] = [float(c) for c in tags[gps['lat_coord']].values]
        tags[gps['lng_coord']] = [float(c) for c in tags[gps['lng_coord']].values]
        tags[gps['lat_ref']] = tags[gps['lat_ref']].values
        tags[gps['lng_ref']] = tags[gps['lng_ref']].values

    lat = __degrees_to_decimal(*tags[gps['lat_coord']])
    if tags[gps['lat_ref']] == 'S':
        lat *= -1

    lng = __degrees_to_decimal(*tags[gps['lng_coord']])
    if tags[gps['lng_ref']] == 'W':
        lng *= -1

    return lat, lng


# ---------------------------------------------------------------------------
# IFD tag representation
# ---------------------------------------------------------------------------


class IfdTag:
    """
    Represents an IFD tag.
    """

    def __init__(
        self,
        printable: str,
        tag: int,
        field_type: FieldType,
        values: Any,
        field_offset: int,
        field_length: int,
        prefer_printable: bool = True,
    ) -> None:
        # printable version of data
        self.printable = printable
        # tag ID number
        self.tag = tag
        # field type as index into FIELD_TYPES
        self.field_type = field_type
        # offset of start of field in bytes from beginning of IFD
        self.field_offset = field_offset
        # length of data field in bytes
        self.field_length = field_length
        # either string, bytes or list of data items
        self.values = values
        # indication if printable version should be used upon serialization
        self.prefer_printable = prefer_printable

    def __str__(self) -> str:
        return self.printable

    def __repr__(self) -> str:
        try:
            tag = '(0x%04X) %s=%s @ %d' % (
                self.tag,
                FIELD_DEFINITIONS[self.field_type][1],
                self.printable,
                self.field_offset,
            )
        except TypeError:
            tag = '(%s) %s=%s @ %s' % (
                str(self.tag),
                FIELD_DEFINITIONS[self.field_type][1],
                self.printable,
                str(self.field_offset),
            )
        return tag


SerializedTagValue = Union[int, float, str, bytes, List[int], List[float], None]
SerializedTagDict = Dict[str, SerializedTagValue]


def convert_types(
    exif_tags: Dict[str, Union[IfdTag, bytes]],
) -> SerializedTagDict:
    """
    Convert Exif IfdTags to built-in Python types for easier serialization and programmatic use.

    - If the printable value of the IfdTag is relevant (e.g. enum type), it is preserved.
    - Otherwise, values are processed based on their field type, with some cleanups applied.
    - Single-element lists are unpacked to return the item directly.
    """

    output: SerializedTagDict = {}

    for tag_name, ifd_tag in exif_tags.items():
        # JPEGThumbnail and TIFFThumbnail are the only values
        # in Exif Tags dict that do not have the IfdTag type.
        if isinstance(ifd_tag, bytes):
            output[tag_name] = ifd_tag
            continue

        convert_func: Callable[[IfdTag, str], SerializedTagValue]

        if ifd_tag.prefer_printable:
            # Prioritize the printable value if prefer_printable is set
            convert_func = convert_proprietary

        else:
            # Get the conversion function based on field type
            try:
                convert_func = conversion_map[ifd_tag.field_type]
            except KeyError:
                logger.error(
                    'Type conversion for field type %s not explicitly supported',
                    ifd_tag.field_type,
                )
                convert_func = convert_proprietary  # Fallback to printable

        output[tag_name] = convert_func(ifd_tag, tag_name)

        # Useful only for testing
        # logger.warning(
        #     f"{convert_func.__name__}: {ifd_tag.field_type} to {type(output[tag_name]).__name__}\n"
        #     f"{tag_name} --> {str(output[tag_name])[:30]!r}"
        # )

    return output


def convert_ascii(ifd_tag: IfdTag, tag_name: str) -> Union[str, bytes, None]:
    """
    Handle ASCII conversion, including special date formats.

    Returns:
    - str
    - bytes for rare ascii sequences that aren't Unicode
    - None for empty values
    """

    out = ifd_tag.values

    # Handle DateTime formatting; often formatted in a way that cannot
    # be parsed by Python dateutil (%Y:%m:%d %H:%M:%S).
    if 'DateTime' in tag_name and len(out) == 19 and out.count(':') == 4:
        out = out.replace(':', '-', 2)

    # Handle GPSDate formatting; these are proper dates with the wrong
    # delimiter (':' rather than '-'). Invalid values have been found
    # in test images: '' and '2014:09:259'
    elif tag_name == 'GPS GPSDate' and len(out) == 10 and out.count(':') == 2:
        out = out.replace(':', '-')

    # Strip occasional trailing whitespaces
    out = out.strip()

    if not out:
        return None

    # Attempt to decode bytes if unicode
    if isinstance(out, bytes):
        try:
            return out.decode()
        except UnicodeDecodeError:
            pass

    return out


def convert_undefined(ifd_tag: IfdTag, _tag_name: str) -> Union[bytes, str, int, None]:
    """
    Handle Undefined type conversion.

    Returns:
    - bytes if not Unicode such as Exif MakerNote
    - str for Unicode
    - int for rare MakerNote Tags containing a single value
    - None for empty values such as some MakerNote Tags
    """

    out = ifd_tag.values

    if len(out) == 1:
        # Return integer from single-element list
        return out[0]

    # These contain bytes represented as a list of integers, sometimes with surrounded by spaces and/or null bytes
    out = bytes(out).strip(b' \x00')

    if not out:
        return None

    # Empty byte sequences or Unicode values should be decoded as strings
    try:
        return out.decode()
    except UnicodeDecodeError:
        return out


def convert_numeric(ifd_tag: IfdTag, _tag_name: str) -> Union[int, List[int], None]:
    """
    Handle numeric types conversion.

    Returns:
    - int in most cases
    - list of int
    - None for empty values such as some MakerNote Tags

    Note: All Floating Point tags seen were empty.
    """

    out = ifd_tag.values

    if not out:  # Empty lists, seen in floating point numbers
        return None

    return out[0] if len(out) == 1 else out


def convert_ratio(ifd_tag: IfdTag, _tag_name: str) -> Union[int, float, List[int], List[float], None]:
    """
    Handle Ratio and Signed Ratio conversion.

    Returns:
    - int when the denominator is 1 or unused
    - float otherwise
    - a list of int or float, such as GPS Latitude/Longitude/TimeStamp
    - None for empty values such as some MakerNote Tags

    Ratios can be re-created with `Fraction(float_value).limit_denominator()`.
    """

    out = ifd_tag.values
    if not out:
        return None
    return out[0] if len(out) == 1 else out


def convert_bytes(ifd_tag: IfdTag, tag_name: str) -> Union[bytes, str, int, None]:
    """
    Handle Byte and Signed Byte conversion.

    Returns:
    - bytes
    - str for Unicode such as GPSVersionID and Image ApplicationNotes (XML)
    - int for single byte values such as GPSAltitudeRef or some MakerNote fields
    - None for empty values such as some MakerNote Tags
    """

    out = ifd_tag.values

    if len(out) == 1:
        # Byte can be a single integer, such as GPSAltitudeRef (0 or 1)
        return out[0]

    if tag_name == 'GPS GPSVersionID':
        return '.'.join(map(str, out))  # e.g. [2, 3, 0, 0] --> '2.3.0.0'

    # Byte sequences are often surrounded by or only composed of spaces and/or null bytes
    out = bytes(out).strip(b' \x00')

    if not out:
        return None

    # Unicode values should be decoded as strings (e.g. XML)
    try:
        return out.decode()
    except UnicodeDecodeError:
        return out


def convert_proprietary(ifd_tag: IfdTag, _tag_name: str) -> Union[str, None]:
    """
    Handle Proprietary type conversion.

    Returns:
    - str as all tags of this made-up type (e.g. enums) prefer printable
    - None for very rare empty printable values
    """

    out = ifd_tag.printable
    if not out or out == '[]':
        return None

    return out


# Mapping of field type to conversion function
conversion_map: Dict[FieldType, Callable] = {
    FieldType.PROPRIETARY: convert_proprietary,
    FieldType.BYTE: convert_bytes,
    FieldType.ASCII: convert_ascii,
    FieldType.SHORT: convert_numeric,
    FieldType.LONG: convert_numeric,
    FieldType.RATIO: convert_ratio,
    FieldType.SIGNED_BYTE: convert_numeric,
    FieldType.UNDEFINED: convert_undefined,
    FieldType.SIGNED_SHORT: convert_numeric,
    FieldType.SIGNED_LONG: convert_numeric,
    FieldType.SIGNED_RATIO: convert_ratio,
    FieldType.FLOAT_32: convert_numeric,
    FieldType.FLOAT_64: convert_numeric,
    FieldType.IFD: convert_bytes,
}


# ---------------------------------------------------------------------------
# HEIC / AVIF format finder
# ---------------------------------------------------------------------------


def find_heic_tiff(fh: BinaryIO) -> Tuple[int, bytes]:
    """
    Look for TIFF header in HEIC files.

    In some HEIC files, the Exif offset is 0,
    and yet there is a plain TIFF header near end of the file.
    """
    data = fh.read(4)
    if data[0:2] in [b'II', b'MM'] and data[2] == 42 and data[3] == 0:
        offset = fh.tell() - 4
        fh.seek(offset)
        endian = data[0:2]
        offset = fh.tell()
        logger.debug('Found TIFF header in Exif, offset = %0xH', offset)
    else:
        raise InvalidExif('Exif pointer to zeros, but found ' + str(data) + ' instead of a TIFF header.')
    return offset, endian


class BoxVersion(ExifError):
    """Wrong box version."""


class BadSize(ExifError):
    """Wrong box size."""


class Box:
    """A HEIC Box."""

    version = 0
    minor_version = 0
    item_count = 0
    size = 0
    after = 0
    pos = 0
    compat: List[bytes] = []
    base_offset = 0
    # this is full of boxes, but not in a predictable order.
    subs: Dict[str, 'Box'] = {}
    locs: Dict = {}
    exif_infe: Optional['Box'] = None
    item_id = 0
    item_type = b''
    item_name = b''
    item_protection_index = 0
    major_brand = b''
    offset_size = 0
    length_size = 0
    base_offset_size = 0
    index_size = 0
    flags = 0
    name: str

    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return "<box '%s'>" % self.name

    def set_sizes(self, offset: int, length: int, base_offset: int, index: int) -> None:
        self.offset_size = offset
        self.length_size = length
        self.base_offset_size = base_offset
        self.index_size = index

    def set_full(self, vflags: int) -> None:
        """
        ISO boxes come in 'old' and 'full' variants.
        The 'full' variant contains version and flags information.
        """
        self.version = vflags >> 24
        self.flags = vflags & 0x00FFFFFF


class HEICExifFinder:
    """Find HEIC EXIF tags."""

    file_handle: BinaryIO

    def __init__(self, file_handle: BinaryIO) -> None:
        self.file_handle = file_handle

    def get(self, nbytes: int) -> bytes:
        read = self.file_handle.read(nbytes)
        if not read:
            raise EOFError
        if len(read) != nbytes:
            msg = 'get(nbytes={nbytes}) found {read} bytes at position {pos}'.format(
                nbytes=nbytes, read=len(read), pos=self.file_handle.tell()
            )
            raise BadSize(msg)
        return read

    def get16(self) -> int:
        return struct.unpack('>H', self.get(2))[0]

    def get32(self) -> int:
        return struct.unpack('>L', self.get(4))[0]

    def get64(self) -> int:
        return struct.unpack('>Q', self.get(8))[0]

    def get_int4x2(self) -> tuple:
        num = struct.unpack('>B', self.get(1))[0]
        num0 = num >> 4
        num1 = num & 0xF
        return num0, num1

    def get_int(self, size: int) -> int:
        """some fields have variant-sized data."""
        if size == 2:
            return self.get16()
        if size == 4:
            return self.get32()
        if size == 8:
            return self.get64()
        if size == 0:
            return 0
        raise BadSize(size)

    def get_string(self) -> bytes:
        read = []
        while 1:
            char = self.get(1)
            if char == b'\x00':
                break
            read.append(char)
        return b''.join(read)

    def next_box(self) -> Box:
        pos = self.file_handle.tell()
        size = self.get32()
        kind = self.get(4).decode('ascii')
        box = Box(kind)
        if size == 0:
            # signifies 'to the end of the file', we shouldn't see this.
            raise NotImplementedError
        if size == 1:
            # 64-bit size follows type.
            size = self.get64()
            box.size = size - 16
            box.after = pos + size
        else:
            box.size = size - 8
            box.after = pos + size
        box.pos = self.file_handle.tell()
        return box

    def get_full(self, box: Box) -> None:
        box.set_full(self.get32())

    def skip(self, box: Box) -> None:
        self.file_handle.seek(box.after)

    def expect_parse(self, name: str) -> Box:
        while True:
            box = self.next_box()
            if box.name == name:
                return self.parse_box(box)
            self.skip(box)

    def get_parser(self, box: Box) -> Optional[Callable[[Box], Any]]:
        defs = {
            'ftyp': self._parse_ftyp,
            'meta': self._parse_meta,
            'infe': self._parse_infe,
            'iinf': self._parse_iinf,
            'iloc': self._parse_iloc,
            'hdlr': self._parse_hdlr,  # HEIC/AVIF hdlr = Handler
            'pitm': self._parse_pitm,  # HEIC/AVIF pitm = Primary Item
            'iref': self._parse_iref,  # HEIC/AVIF idat = Item Reference
            'idat': self._parse_idat,  # HEIC/AVIF idat = Item Data Box
            'dinf': self._parse_dinf,  # HEIC/AVIF dinf = Data Information Box
            'iprp': self._parse_iprp,  # HEIC/AVIF iprp = Item Protection Box
        }
        return defs.get(box.name)

    def parse_box(self, box: Box) -> Box:
        probe = self.get_parser(box)
        if probe is not None:
            probe(box)
        # in case anything is left unread
        self.file_handle.seek(box.after)
        return box

    def _parse_ftyp(self, box: Box) -> None:
        box.major_brand = self.get(4)
        box.minor_version = self.get32()
        box.compat = []
        size = box.size - 8
        while size > 0:
            box.compat.append(self.get(4))
            size -= 4

    def _parse_meta(self, meta: Box) -> None:
        self.get_full(meta)
        while self.file_handle.tell() < meta.after:
            box = self.next_box()
            psub = self.get_parser(box)
            if psub is not None:
                psub(box)
                meta.subs[box.name] = box
            else:
                logger.debug('HEIC: skipping %r', box)
            # skip any unparsed data
            self.skip(box)

    def _parse_infe(self, box: Box) -> None:
        self.get_full(box)
        if box.version >= 2:
            if box.version == 2:
                box.item_id = self.get16()
            elif box.version == 3:
                box.item_id = self.get32()
            box.item_protection_index = self.get16()
            box.item_type = self.get(4)
            box.item_name = self.get_string()
            # ignore the rest

    def _parse_iinf(self, box: Box) -> None:
        self.get_full(box)
        count = self.get16()
        box.exif_infe = None
        for _ in range(count):
            infe = self.expect_parse('infe')
            if infe.item_type == b'Exif':
                logger.debug("HEIC: found Exif 'infe' box")
                box.exif_infe = infe
                break

    def _parse_iloc(self, box: Box) -> None:
        self.get_full(box)
        size0, size1 = self.get_int4x2()
        size2, size3 = self.get_int4x2()
        box.set_sizes(size0, size1, size2, size3)
        if box.version < 2:
            box.item_count = self.get16()
        elif box.version == 2:
            box.item_count = self.get32()
        else:
            raise BoxVersion(2, box.version)
        box.locs = {}
        logger.debug('HEIC: %d iloc items', box.item_count)
        for _ in range(box.item_count):
            if box.version < 2:
                item_id = self.get16()
            elif box.version == 2:
                item_id = self.get32()
            else:
                # notreached
                raise BoxVersion(2, box.version)
            if box.version in (1, 2):
                # ignore construction_method
                self.get16()
            # ignore data_reference_index
            self.get16()
            box.base_offset = self.get_int(box.base_offset_size)
            extent_count = self.get16()
            extents = []
            for _ in range(extent_count):
                if box.version in (1, 2) and box.index_size > 0:
                    self.get_int(box.index_size)
                extent_offset = self.get_int(box.offset_size)
                extent_length = self.get_int(box.length_size)
                extents.append((extent_offset, extent_length))
            box.locs[item_id] = extents

    # Added a few box names, which as unhandled aborted data extraction:
    # hdlr, pitm, dinf, iprp, idat, iref
    #
    # Handling is initially `None`.
    # They were found in .heif photo files produced by Nokia 8.3 5G.
    #
    # They are part of the standard, referring to:
    #   - ISO/IEC 14496-12 fifth edition 2015-02-20 (chapter 8.10 Metadata)
    #     found in:
    #     https://mpeg.chiariglione.org/standards/mpeg-4/iso-base-media-file-format/text-isoiec-14496-12-5th-edition
    #     (The newest is ISO/IEC 14496-12:2022, but would cost 208 Swiss Francs at iso.org)
    #   - A C++ example: https://exiv2.org/book/#BMFF

    def _parse_hdlr(self, box: Box) -> None:
        logger.debug("HEIC: found 'hdlr' Box %s, skipped", box.name)

    def _parse_pitm(self, box: Box) -> None:
        logger.debug("HEIC: found 'pitm' Box %s, skipped", box.name)

    def _parse_dinf(self, box: Box) -> None:
        logger.debug("HEIC: found 'dinf' Box %s, skipped", box.name)

    def _parse_iprp(self, box: Box) -> None:
        logger.debug("HEIC: found 'iprp' Box %s, skipped", box.name)

    def _parse_idat(self, box: Box) -> None:
        logger.debug("HEIC: found 'idat' Box %s, skipped", box.name)

    def _parse_iref(self, box: Box) -> None:
        logger.debug("HEIC: found 'iref' Box %s, skipped", box.name)

    def find_exif(self) -> Tuple[int, bytes]:
        ftyp = self.expect_parse('ftyp')
        if ftyp.major_brand not in [b'heic', b'avif', b'mif1'] or ftyp.minor_version != 0:
            return 0, b''

        meta = self.expect_parse('meta')
        if meta.subs['iinf'].exif_infe is None:
            return 0, b''

        item_id = meta.subs['iinf'].exif_infe.item_id
        extents = meta.subs['iloc'].locs[item_id]
        logger.debug('HEIC: found Exif location.')
        # we expect the Exif data to be in one piece.
        assert len(extents) == 1
        pos, _ = extents[0]
        # looks like there's a kind of pseudo-box here.
        self.file_handle.seek(pos)
        # the payload of "Exif" item may be start with either
        # b'\xFF\xE1\xSS\xSSExif\x00\x00' (with APP1 marker, e.g. Android Q)
        # or
        # b'Exif\x00\x00' (without APP1 marker, e.g. iOS)
        # according to "ISO/IEC 23008-12, 2017-12", both of them are legal
        exif_tiff_header_offset = self.get32()

        if exif_tiff_header_offset == 0:
            # This case was found in HMD Nokia 8.3 5G heic photos.
            # The TIFF header just sits there without any 'Exif'.
            offset = 0
            endian = b'?'  # Haven't got Endian info yet
        else:
            assert exif_tiff_header_offset >= 6
            assert self.get(exif_tiff_header_offset)[-6:] == b'Exif\x00\x00'
            offset = self.file_handle.tell()
            endian = self.file_handle.read(1)

        return offset, endian


# ---------------------------------------------------------------------------
# JPEG XL format finder
# ---------------------------------------------------------------------------


class JXLExifFinder(HEICExifFinder):
    """Find JPEG XL EXIF tags."""

    def find_exif(self) -> Tuple[int, bytes]:
        ftyp = self.expect_parse('ftyp')
        assert ftyp.major_brand == b'jxl '
        assert ftyp.minor_version == 0
        exif = self.expect_parse('Exif')

        offset = exif.pos + 4
        self.file_handle.seek(offset - 8)
        assert self.get(8)[:6] == b'Exif\x00\x00'
        endian = self.file_handle.read(1)
        return offset, endian


# ---------------------------------------------------------------------------
# JPEG format finder
# ---------------------------------------------------------------------------


def _increment_base(data, base) -> int:
    return __ord(data[base + 2]) * 256 + __ord(data[base + 3]) + 2


def _get_initial_base(fh: BinaryIO, data: bytes, fake_exif: int) -> Tuple[int, int]:
    base = 2
    logger.debug(
        'data[2]=0x%X data[3]=0x%X data[6:10]=%s',
        __ord(data[2]),
        __ord(data[3]),
        data[6:10],
    )
    while __ord(data[2]) == 0xFF and data[6:10] in (b'JFIF', b'JFXX', b'OLYM', b'Phot'):
        length = __ord(data[4]) * 256 + __ord(data[5])
        logger.debug(' Length offset is %s', length)
        fh.read(length - 8)
        # fake an EXIF beginning of file
        # I don't think this is used. --gd
        data = b'\xff\x00' + fh.read(10)
        fake_exif = 1
        if base > 2:
            logger.debug(' Added to base')
            base = base + length + 4 - 2
        else:
            logger.debug(' Added to zero')
            base = length + 4
        logger.debug(' Set segment base to 0x%X', base)
    return base, fake_exif


def _get_base(base: int, data: bytes) -> int:
    # pylint: disable=too-many-statements
    while True:
        logger.debug(' Segment base 0x%X', base)
        if data[base : base + 2] == b'\xff\xe1':
            # APP1
            logger.debug('  APP1 at base 0x%X', base)
            logger.debug('  Length: 0x%X 0x%X', __ord(data[base + 2]), __ord(data[base + 3]))
            logger.debug('  Code: %s', data[base + 4 : base + 8])
            if data[base + 4 : base + 8] == b'Exif':
                logger.debug('  Decrement base by 2 to get to pre-segment header (for compatibility with later code)')
                base -= 2
                break
            increment = _increment_base(data, base)
            logger.debug(' Increment base by %s', increment)
            base += increment
        elif data[base : base + 2] == b'\xff\xe0':
            # APP0
            logger.debug('  APP0 at base 0x%X', base)
            logger.debug('  Length: 0x%X 0x%X', __ord(data[base + 2]), __ord(data[base + 3]))
            logger.debug('  Code: %s', data[base + 4 : base + 8])
            increment = _increment_base(data, base)
            logger.debug(' Increment base by %s', increment)
            base += increment
        elif data[base : base + 2] == b'\xff\xe2':
            # APP2
            logger.debug('  APP2 at base 0x%X', base)
            logger.debug('  Length: 0x%X 0x%X', __ord(data[base + 2]), __ord(data[base + 3]))
            logger.debug(' Code: %s', data[base + 4 : base + 8])
            increment = _increment_base(data, base)
            logger.debug(' Increment base by %s', increment)
            base += increment
        elif data[base : base + 2] == b'\xff\xee':
            # APP14
            logger.debug('  APP14 Adobe segment at base 0x%X', base)
            logger.debug('  Length: 0x%X 0x%X', __ord(data[base + 2]), __ord(data[base + 3]))
            logger.debug('  Code: %s', data[base + 4 : base + 8])
            increment = _increment_base(data, base)
            logger.debug(' Increment base by %s', increment)
            base += increment
            logger.debug('  There is useful EXIF-like data here, but we have no parser for it.')
        elif data[base : base + 2] == b'\xff\xdb':
            logger.debug('  JPEG image data at base 0x%X No more segments are expected.', base)
            break
        elif data[base : base + 2] == b'\xff\xd8':
            # APP12
            logger.debug('  FFD8 segment at base 0x%X', base)
            logger.debug(
                '  Got 0x%X 0x%X and %s instead',
                __ord(data[base]),
                __ord(data[base + 1]),
                data[4 + base : 10 + base],
            )
            logger.debug('  Length: 0x%X 0x%X', __ord(data[base + 2]), __ord(data[base + 3]))
            logger.debug('  Code: %s', data[base + 4 : base + 8])
            increment = _increment_base(data, base)
            logger.debug('  Increment base by %s', increment)
            base += increment
        elif data[base : base + 2] == b'\xff\xec':
            # APP12
            logger.debug('  APP12 XMP (Ducky) or Pictureinfo segment at base 0x%X', base)
            logger.debug('  Got 0x%X and 0x%X instead', __ord(data[base]), __ord(data[base + 1]))
            logger.debug('  Length: 0x%X 0x%X', __ord(data[base + 2]), __ord(data[base + 3]))
            logger.debug('Code: %s', data[base + 4 : base + 8])
            increment = _increment_base(data, base)
            logger.debug('  Increment base by %s', increment)
            base += increment
            logger.debug(
                ('  There is useful EXIF-like data here (quality, comment, copyright), but we have no parser for it.')
            )
        else:
            try:
                increment = _increment_base(data, base)
                logger.debug(
                    '  Got 0x%X and 0x%X instead',
                    __ord(data[base]),
                    __ord(data[base + 1]),
                )
            except IndexError as err:
                raise InvalidExif('Unexpected/unhandled segment type or file content.') from err
            logger.debug('  Increment base by %s', increment)
            base += increment
    return base


def find_jpeg_exif(fh: BinaryIO, data: bytes, fake_exif: int) -> Tuple[int, bytes, int]:
    logger.debug('JPEG format recognized data[0:2]=0x%X%X', __ord(data[0]), __ord(data[1]))

    base, fake_exif = _get_initial_base(fh, data, fake_exif)

    # Big ugly patch to deal with APP2 (or other) data coming before APP1
    fh.seek(0)
    # in theory, this could be insufficient since 64K is the maximum size--gd
    data = fh.read(base + 4000)

    base = _get_base(base, data)

    fh.seek(base + 12)
    if __ord(data[2 + base]) == 0xFF and data[6 + base : 10 + base] == b'Exif':
        # detected EXIF header
        offset = fh.tell()
        endian = fh.read(1)
        # HACK TEST:  endian = 'M'
    elif __ord(data[2 + base]) == 0xFF and data[6 + base : 10 + base + 1] == b'Ducky':
        # detected Ducky header.
        logger.debug(
            'EXIF-like header (normally 0xFF and code): 0x%X and %s',
            __ord(data[2 + base]),
            data[6 + base : 10 + base + 1],
        )
        offset = fh.tell()
        endian = fh.read(1)
    elif __ord(data[2 + base]) == 0xFF and data[6 + base : 10 + base + 1] == b'Adobe':
        # detected APP14 (Adobe)
        logger.debug(
            'EXIF-like header (normally 0xFF and code): 0x%X and %s',
            __ord(data[2 + base]),
            data[6 + base : 10 + base + 1],
        )
        offset = fh.tell()
        endian = fh.read(1)
    else:
        # no EXIF information
        msg = 'No EXIF header expected data[2+base]==0xFF and data[6+base:10+base]===Exif (or Duck)'
        msg += ' Did get 0x%X and %r' % (
            __ord(data[2 + base]),
            data[6 + base : 10 + base + 1],
        )
        raise InvalidExif(msg)
    return offset, endian, fake_exif


# ---------------------------------------------------------------------------
# EXIF type / endian helpers
# ---------------------------------------------------------------------------

ENDIAN_TYPES: Dict[str, str] = {
    'I': 'Intel',
    'M': 'Motorola',
    '\x01': 'Adobe Ducky',
    'b': 'XMP/Adobe unknown',
}


def get_endian_str(endian_bytes) -> Tuple[str, str]:
    endian_str = chr(__ord(endian_bytes[0]))
    return endian_str, ENDIAN_TYPES.get(endian_str, 'Unknown')


def find_tiff_exif(fh: BinaryIO) -> Tuple[int, bytes]:
    logger.debug('TIFF format recognized in data[0:2]')
    fh.seek(0)
    endian = fh.read(1)
    fh.read(1)
    offset = 0
    return offset, endian


def find_webp_exif(fh: BinaryIO) -> Tuple[int, bytes]:
    logger.debug('WebP format recognized in data[0:4], data[8:12]')
    # file specification: https://developers.google.com/speed/webp/docs/riff_container
    data = fh.read(5)
    if data[0:4] == b'VP8X' and data[4] & 8:
        # https://developers.google.com/speed/webp/docs/riff_container#extended_file_format
        fh.seek(13, 1)
        while True:
            data = fh.read(8)  # Chunk FourCC (32 bits) and Chunk Size (32 bits)
            if len(data) != 8:
                raise InvalidExif('Invalid webp file chunk header.')
            if data[0:4] == b'EXIF':
                fh.seek(6, 1)
                offset = fh.tell()
                endian = fh.read(1)
                return offset, endian
            size = struct.unpack('<L', data[4:8])[0]
            fh.seek(size, 1)
    raise ExifNotFound('Webp file does not have exif data.')


def find_png_exif(fh: BinaryIO, data: bytes) -> Tuple[int, bytes]:
    logger.debug('PNG format recognized in data[0:8]=%s', data[:8].hex())
    fh.seek(8)

    while True:
        data = fh.read(8)
        chunk = data[4:8]
        logger.debug('PNG found chunk %s', chunk.decode('ascii'))

        if chunk in (b'', b'IEND'):
            break
        if chunk == b'eXIf':
            offset = fh.tell()
            return offset, fh.read(1)

        chunk_size = int.from_bytes(data[:4], 'big')
        fh.seek(fh.tell() + chunk_size + 4)

    raise ExifNotFound('PNG file does not have exif data.')


def find_jxl_exif(fh: BinaryIO) -> Tuple[int, bytes]:
    logger.debug('JPEG XL format recognized in data[0:12]')

    fh.seek(0)
    jxl = JXLExifFinder(fh)
    offset, endian = jxl.find_exif()
    if offset > 0:
        return offset, endian

    raise ExifNotFound('JPEG XL file does not have exif data.')


def determine_type(fh: BinaryIO) -> Tuple[int, bytes, int]:
    # by default do not fake an EXIF beginning
    fake_exif = 0

    data = fh.read(12)
    if data[0:2] in [b'II', b'MM']:
        # it's a TIFF file
        offset, endian = find_tiff_exif(fh)
    elif data[4:12] in [b'ftypheic', b'ftypavif', b'ftypmif1']:
        fh.seek(0)
        heic = HEICExifFinder(fh)
        offset, endian = heic.find_exif()
        if offset == 0:
            offset, endian = find_heic_tiff(fh)
            # It's a HEIC file with a TIFF header
    elif data[0:4] == b'RIFF' and data[8:12] == b'WEBP':
        offset, endian = find_webp_exif(fh)
    elif data[0:2] == b'\xff\xd8':
        # it's a JPEG file
        offset, endian, fake_exif = find_jpeg_exif(fh, data, fake_exif)
    elif data[0:8] == b'\x89PNG\r\n\x1a\n':
        offset, endian = find_png_exif(fh, data)
    elif data == b'\0\0\0\x0cJXL\x20\x0d\x0a\x87\x0a':
        offset, endian = find_jxl_exif(fh)
    else:
        raise ExifNotFound('File format not recognized.')
    return offset, endian, fake_exif


# ---------------------------------------------------------------------------
# XMP helpers
# ---------------------------------------------------------------------------


def find_xmp_data(fh: BinaryIO) -> bytes:
    xmp_bytes = b''
    logger.debug('XMP not in Exif, searching file for XMP info...')
    xml_started = False
    xml_finished = False
    for line in fh:
        open_tag = line.find(b'<x:xmpmeta')
        close_tag = line.find(b'</x:xmpmeta>')
        if open_tag != -1:
            xml_started = True
            line = line[open_tag:]
            logger.debug('XMP found opening tag at line position %s', open_tag)
        if close_tag != -1:
            logger.debug('XMP found closing tag at line position %s', close_tag)
            line_offset = 0
            if open_tag != -1:
                line_offset = open_tag
            line = line[: (close_tag - line_offset) + 12]
            xml_finished = True
        if xml_started:
            xmp_bytes += line
        if xml_finished:
            break
    logger.debug('Found %s XMP bytes', len(xmp_bytes))
    return xmp_bytes


def xmp_bytes_to_str(xmp_bytes: bytes) -> str:
    """Adobe's Extensible Metadata Platform, just dump the pretty XML."""

    logger.debug('Cleaning XMP data ...')

    # Pray that it's encoded in UTF-8
    # TODO: allow user to specify encoding
    xmp_string = xmp_bytes.decode('utf-8')

    try:
        pretty = parseString(xmp_string).toprettyxml()
    except ExpatError:
        logger.warning('XMP: XML is not well formed')
        return xmp_string
    cleaned = []
    for line in pretty.splitlines():
        if line.strip():
            cleaned.append(line)
    return '\n'.join(cleaned)


# ---------------------------------------------------------------------------
# ExifHeader – main EXIF processor
# ---------------------------------------------------------------------------


class ExifHeader:
    """
    Handle an EXIF header.
    """

    def __init__(
        self,
        file_handle: BinaryIO,
        endian: str,
        offset: int,
        fake_exif: int,
        strict: bool,
        debug=False,
        detailed=True,
        truncate_tags=True,
    ) -> None:
        self.file_handle = file_handle
        self.endian = endian
        self.offset = offset
        self.fake_exif = fake_exif
        self.strict = strict
        self.debug = debug
        self.detailed = detailed
        self.truncate_tags = truncate_tags
        self.tags: Dict[str, Any] = {}

    def s2n(self, offset: int, length: int, signed=False) -> int:
        """
        Convert slice to integer, based on sign and endian flags.

        Usually this offset is assumed to be relative to the beginning of the
        start of the EXIF information.
        For some cameras that use relative tags, this offset may be relative
        to some other starting point.
        """
        # Little-endian if Intel, big-endian if Motorola
        fmt = '<' if self.endian == 'I' else '>'
        # Construct a format string from the requested length and signedness;
        # raise a ValueError if length is something silly like 3
        try:
            fmt += {
                (1, False): 'B',
                (1, True): 'b',
                (2, False): 'H',
                (2, True): 'h',
                (4, False): 'I',
                (4, True): 'i',
                (8, False): 'L',
                (8, True): 'l',
            }[(length, signed)]
        except KeyError as err:
            raise ValueError('unexpected unpacking length: %d' % length) from err
        self.file_handle.seek(self.offset + offset)
        buf = self.file_handle.read(length)

        if buf:
            # Make sure the buffer is the proper length.
            # Allows bypassing of corrupt slices.
            if len(buf) != length:
                logger.warning('Unexpected slice length: %d', len(buf))
                return 0
            return struct.unpack(fmt, buf)[0]
        return 0

    def n2b(self, offset: int, length: int) -> bytes:
        """Convert offset to bytes."""
        s = b''
        for _ in range(length):
            if self.endian == 'I':
                s += bytes([offset & 0xFF])
            else:
                s = bytes([offset & 0xFF]) + s
            offset = offset >> 8
        return s

    def _first_ifd(self) -> int:
        """Return first IFD."""
        return self.s2n(4, 4)

    def _next_ifd(self, ifd: int) -> int:
        """Return the pointer to next IFD."""
        entries = self.s2n(ifd, 2)
        next_ifd = self.s2n(ifd + 2 + 12 * entries, 4)
        if next_ifd == ifd:
            return 0
        return next_ifd

    def list_ifd(self) -> List[int]:
        """Return the list of IFDs in the header."""
        i = self._first_ifd()
        ifds = []
        set_ifds = set()
        while i:
            if i in set_ifds:
                logger.warning('IFD loop detected.')
                break
            set_ifds.add(i)
            ifds.append(i)
            i = self._next_ifd(i)
        return ifds

    def _process_field(
        self,
        tag_name: str,
        count: int,
        field_type: int,
        type_length: int,
        offset: int,
    ) -> list:
        values: List[Any] = []
        signed = field_type in SIGNED_FIELD_TYPES
        # TODO: investigate
        # some entries get too big to handle could be malformed
        # file or problem with self.s2n
        if count < 1000:
            for _ in range(count):
                if field_type in RATIO_FIELD_TYPES:
                    # A rational number Fraction
                    numerator = self.s2n(offset, 4, signed)
                    denominator = self.s2n(offset + 4, 4, signed)
                    if denominator == 0:
                        logger.warning('Zero denominator for field %s', tag_name)
                        ratio_value = Fraction(numerator, 1)
                    else:
                        ratio_value = Fraction(numerator, denominator)
                    values.append(ratio_value)
                elif field_type in FLOAT_FIELD_TYPES:
                    # a float or double
                    unpack_format = ''
                    if self.endian == 'I':
                        unpack_format += '<'
                    else:
                        unpack_format += '>'
                    if field_type == FieldType.FLOAT_32:
                        unpack_format += 'f'
                    else:
                        unpack_format += 'd'
                    self.file_handle.seek(self.offset + offset)
                    byte_str = self.file_handle.read(type_length)
                    try:
                        values.append(struct.unpack(unpack_format, byte_str))
                    except struct.error:
                        logger.warning('Possibly corrupted field %s', tag_name)

                else:
                    value = self.s2n(offset, type_length, signed)
                    values.append(value)

                offset = offset + type_length

        return values

    def _process_ascii_field(self, ifd_name: str, tag_name: str, count: int, offset: int):
        values: Union[str, bytes] = ''
        # special case: null-terminated ASCII string
        # XXX investigate
        # sometimes gets too big to fit in int value
        if count != 0:  # and count < (2**31):  # 2E31 is hardware dependent. --gd
            file_position = self.offset + offset
            try:
                self.file_handle.seek(file_position)
                values = self.file_handle.read(count)
                # Drop any garbage after a null.
                values = values.split(b'\x00', 1)[0]
                if isinstance(values, bytes):
                    try:
                        values = values.decode('utf-8')
                    except UnicodeDecodeError:
                        logger.warning('Possibly corrupted field %s in %s IFD', tag_name, ifd_name)
            except OverflowError:
                logger.warning('OverflowError at position: %s, length: %s', file_position, count)
                values = ''
            except MemoryError:
                logger.warning('MemoryError at position: %s, length: %s', file_position, count)
                values = ''
        return values

    def _get_printable_for_field(
        self,
        count: int,
        values: Union[str, list],
        field_type: FieldType,
        tag_entry: IfdDictValue,
        stop_tag: str,
    ) -> Tuple[str, bool]:
        # TODO: use only one type
        if count == 1 and field_type != FieldType.ASCII:
            printable = str(values[0])
        elif count > 50 and len(values) > 20 and not isinstance(values, str):
            if self.truncate_tags:  # NOQA
                printable = str(values[0:20])[0:-1] + ', ... ]'
            else:
                printable = str(values[0:-1])
        else:
            printable = str(values)

        prefer_printable = False

        # compute printable version of values
        if tag_entry:  # NOQA
            # optional 2nd tag element is present
            if tag_entry[1] is not None:
                prefer_printable = True

                # call mapping function
                if callable(tag_entry[1]):
                    printable = tag_entry[1](values)
                # handle sub-ifd
                elif isinstance(tag_entry[1], tuple):
                    ifd_info = tag_entry[1]
                    try:
                        logger.debug('%s SubIFD at offset %d:', ifd_info[0], values[0])
                        self.dump_ifd(
                            ifd=values[0],  # type: ignore
                            stop_tag=stop_tag,
                            ifd_name=ifd_info[0],
                            tag_dict=ifd_info[1],
                        )
                    except IndexError:
                        logger.warning('No values found for %s SubIFD', ifd_info[0])
                else:
                    printable = ''
                    for val in values:
                        # use lookup table for this tag
                        printable += tag_entry[1].get(val, repr(val))

        return printable, prefer_printable

    def _process_tag(
        self,
        ifd: int,
        ifd_name: str,
        tag_entry: SubIfdTagDictValue,
        entry: int,
        tag: int,
        tag_name: str,
        relative: bool,
        stop_tag: str,
    ) -> None:
        field_type_id = self.s2n(entry + 2, 2)
        try:
            field_type = FieldType(field_type_id)
        except ValueError as err:
            if self.strict:
                raise ValueError('Unknown field type %d in tag 0x%04X' % (field_type_id, tag)) from err
            return

        # Not handled
        if field_type == FieldType.PROPRIETARY:
            if self.strict:
                raise ValueError('Unknown field type %d in tag 0x%04X' % (field_type_id, tag))
            return

        type_length = FIELD_DEFINITIONS[field_type][0]
        count = self.s2n(entry + 4, 4)
        # Adjust for tag id/type/count (2+2+4 bytes)
        # Now we point at either the data or the 2nd level offset
        offset = entry + 8

        # If the value fits in 4 bytes, it is inlined, else we
        # need to jump ahead again.
        if count * type_length > 4:
            # offset is not the value; it's a pointer to the value
            # if relative we set things up so s2n will seek to the right
            # place when it adds self.offset.  Note that this 'relative'
            # is for the Nikon type 3 makernote.  Other cameras may use
            # other relative offsets, which would have to be computed here
            # slightly differently.
            if relative:
                tmp_offset = self.s2n(offset, 4)
                offset = tmp_offset + ifd - 8
                if self.fake_exif:
                    offset += 18
            else:
                offset = self.s2n(offset, 4)

        field_offset = offset
        if field_type == FieldType.ASCII:
            values = self._process_ascii_field(ifd_name, tag_name, count, offset)
        else:
            values = self._process_field(tag_name, count, field_type, type_length, offset)

        printable, prefer_printable = self._get_printable_for_field(count, values, field_type, tag_entry, stop_tag)

        self.tags[ifd_name + ' ' + tag_name] = IfdTag(
            printable,
            tag,
            field_type,
            values,
            field_offset,
            count * type_length,
            prefer_printable,
        )
        tag_value = repr(self.tags[ifd_name + ' ' + tag_name])
        logger.debug(' %s: %s', tag_name, tag_value)

    def dump_ifd(
        self,
        ifd: int,
        ifd_name: str,
        tag_dict=None,
        relative=0,
        stop_tag=DEFAULT_STOP_TAG,
    ) -> None:
        """Return a list of entries in the given IFD."""

        # make sure we can process the entries
        if tag_dict is None:
            tag_dict = EXIF_TAGS
        try:
            entries = self.s2n(ifd, 2)
        except TypeError:
            logger.warning('Possibly corrupted IFD: %s', ifd_name)
            return

        for i in range(entries):
            # entry is index of start of this IFD in the file
            entry = ifd + 2 + 12 * i
            tag = self.s2n(entry, 2)

            # get tag name early to avoid errors, help debug
            tag_entry = tag_dict.get(tag)
            if tag_entry:  # NOQA
                tag_name = tag_entry[0]
            else:
                tag_name = f'Tag 0x{tag:04X}'

            # ignore certain tags for faster processing
            if not (not self.detailed and tag in IGNORE_TAGS):
                self._process_tag(ifd, ifd_name, tag_entry, entry, tag, tag_name, relative, stop_tag)

            if tag_name == stop_tag:
                break

    def parse_xmp(self, xmp_bytes: bytes):
        """Adobe's Extensible Metadata Platform, just dump the pretty XML."""

        logger.debug('XMP cleaning data')
        self.tags['Image ApplicationNotes'] = IfdTag(xmp_bytes_to_str(xmp_bytes), 0, FieldType.BYTE, xmp_bytes, 0, 0)
