#!/usr/bin/env python3
#
#
# Library to extract Exif information from digital camera image files.
# https://github.com/ianare/exif-py
#
#
# Copyright (c) 2002-2007 Gene Cash
# Copyright (c) 2007-2025 Ianaré Sévi and contributors
#
# See LICENSE.txt file for licensing information
# See ChangeLog.rst file for all contributors and changes
#

"""
Runs Exif extraction in command line.
"""

import argparse
import sys
import timeit

from imgdb.exifpy import __version__, process_file
from imgdb.exifpy.core import ExifError
from imgdb.exifpy.tags import FIELD_DEFINITIONS
from imgdb.log import log


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog='EXIF.py', description='Extract EXIF information from digital image files.')
    parser.add_argument(
        'files',
        metavar='FILE',
        type=str,
        nargs='+',
        help='files to process',
    )
    parser.add_argument(
        '-v',
        '--version',
        action='version',
        version='EXIF.py Version %s on Python%s' % (__version__, sys.version_info[0]),
        help='Display version information and exit',
    )
    parser.add_argument(
        '-q',
        '--quick',
        action='store_false',
        dest='detailed',
        help='Do not process MakerNotes and do not extract thumbnails',
    )
    parser.add_argument(
        '-s',
        '--strict',
        action='store_true',
        dest='strict',
        help='Run in strict mode (stop on errors).',
    )
    parser.add_argument(
        '-d',
        '--debug',
        action='store_true',
        dest='debug',
        help='Run in debug mode (display extra info).',
    )
    args = parser.parse_args()
    return args


def run_cli(args: argparse.Namespace) -> None:
    """Extract tags based on options (args)."""

    # output info for each file
    for filename in args.files:
        # avoid errors when printing to console
        escaped_fn = filename.encode(sys.getfilesystemencoding(), 'surrogateescape').decode()

        file_start = timeit.default_timer()
        try:
            with open(escaped_fn, 'rb') as img_file:
                log.info('Opening: %s', escaped_fn)

                tag_start = timeit.default_timer()
                # get the tags
                data = process_file(
                    img_file,
                    builtin_types=False,
                    details=args.detailed,
                    strict=args.strict,
                    debug=args.debug,
                )
                tag_stop = timeit.default_timer()

        except IOError:
            log.error("'%s' is unreadable", escaped_fn)
            continue

        if not data:
            log.warning('No EXIF information found')
            print()
            continue

        for field in sorted(data):
            value = data[field]
            try:
                log.info(
                    '%s (%s): %s',
                    field,
                    FIELD_DEFINITIONS[value.field_type][1],
                    value.printable,
                )
            except (ExifError, ValueError):
                log.error('%s: %s', field, str(value))

        file_stop = timeit.default_timer()

        log.debug('Tags processed in %s seconds', tag_stop - tag_start)
        log.debug('File processed in %s seconds', file_stop - file_start)
        print()


def main() -> None:
    run_cli(get_args())


if __name__ == '__main__':
    main()
