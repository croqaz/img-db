"""
Read Exif metadata from image files.
Originally from exif-PY:
https://github.com/ianare/exif-py
"""

from typing import Any, BinaryIO, Dict

from ..log import log
from .core import (
    ExifHeader,
    ExifNotFound,
    InvalidExif,
    convert_types,
    determine_type,
    find_xmp_data,
    get_endian_str,
)

__version__ = '3.5.1'


def process_file(
    fh: BinaryIO,
    details=False,
    strict=False,
    debug=False,
    truncate_tags=True,
    builtin_types=True,
    auto_seek=False,
) -> Dict[str, Any]:
    """
    Process an image file to extract EXIF metadata.

    This is the function that has to deal with all the arbitrary nasty bits
    of the EXIF standard.

    :param fh: the file to process, must be opened in binary mode.
    :param details: If `True`, process MakerNotes.
    :param strict: If `True`, raise exceptions on errors.
    :param debug: Output debug information.
    :param truncate_tags: If `True`, truncate the `printable` tag output.
        There is no effect on tag `values`.
    :param auto_seek: If `True`, automatically `seek` to the start of the file.
    :param builtin_types: If `True`, convert tags to standard Python types.

    :returns: A `dict` containing the EXIF metadata.
        The keys are a string in the format `"IFD_NAME TAG_NAME"`.
        If `builtin_types` is `False`, the value will be a `IfdTag` class, or bytes.
        IF `builtin_types` is `True`, the value will be a standard Python type.
    """

    if auto_seek:
        fh.seek(0)

    try:
        offset, endian_bytes, fake_exif = determine_type(fh)
    except ExifNotFound as err:
        log.warning(err)
        return {}
    except InvalidExif as err:
        log.debug(err)
        return {}

    endian_str, endian_type = get_endian_str(endian_bytes)
    # deal with the EXIF info we found
    log.debug('Endian format is %s (%s)', endian_str, endian_type)

    hdr = ExifHeader(fh, endian_str, offset, fake_exif, strict, debug, details, truncate_tags)
    for ctr, ifd in enumerate(hdr.list_ifd()):
        if ctr == 0:
            ifd_name = 'Image'
        elif ctr == 1:
            ifd_name = 'Thumbnail'
        else:
            ifd_name = 'IFD %d' % ctr
        log.debug('IFD %d (%s) at offset %s:', ctr, ifd_name, ifd)
        hdr.dump_ifd(ifd=ifd, ifd_name=ifd_name)

    # EXIF IFD
    exif_off = hdr.tags.get('Image ExifOffset')
    if exif_off:
        log.debug('Exif SubIFD at offset %s:', exif_off.values[0])
        hdr.dump_ifd(ifd=exif_off.values[0], ifd_name='EXIF')

    # EXIF SubIFD
    sub_ifds = hdr.tags.get('Image SubIFDs')
    if details and sub_ifds:
        for subifd_id, subifd_offset in enumerate(sub_ifds.values):
            log.debug('Exif SubIFD%d at offset %d:', subifd_id, subifd_offset)
            hdr.dump_ifd(ifd=subifd_offset, ifd_name=f'EXIF SubIFD{subifd_id}')

    # parse XMP tags (experimental)
    if debug and details:
        xmp_tag = hdr.tags.get('Image ApplicationNotes')
        if xmp_tag:
            log.debug('XMP present in Exif')
            xmp_bytes = bytes(xmp_tag.values)
        # We need to look in the entire file for the XML
        else:
            xmp_bytes = find_xmp_data(fh)
        if xmp_bytes:
            hdr.parse_xmp(xmp_bytes)

    if builtin_types:
        return convert_types(hdr.tags)

    return hdr.tags
