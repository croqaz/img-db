import re
import os
import shutil
from argparse import ArgumentParser
from time import monotonic
from os.path import isdir
from pathlib import Path

from .main import main


def parse_args():
    cmdline = ArgumentParser()
    cmdline.add_argument('folders', nargs='+', type=Path)
    cmdline.add_argument('--db', help='DB/cache file location')
    cmdline.add_argument('--query', action='store_true', help='DB/cache query')
    cmdline.add_argument('--move', help='move in the database folder')
    cmdline.add_argument('--copy', help='copy in the database folder')
    cmdline.add_argument('--uid',
                         default='{blake2b}',
                         help='the UID is used to calculate the uniqueness of the img, BE CAREFUL')
    cmdline.add_argument('--filter', help='only filter images that match specified RE pattern')
    cmdline.add_argument('--hashes', default='blake2b', help='content hashing, eg: BLAKE2b, SHA256, etc')
    cmdline.add_argument('--v-hashes', default='dhash', help='perceptual hashing (ahash, dhash, vhash, phash)')
    cmdline.add_argument('--exts', help='filter by extension, eg: JPG, PNG, etc')
    cmdline.add_argument('--ignore-sz', type=int, default=128, help='ignore images smaller than')
    cmdline.add_argument('--thumb-sz', type=int, default=128, help='DB thumb size')
    cmdline.add_argument('--thumb-qual', type=int, default=70, help='DB thumb quality')
    cmdline.add_argument('--thumb-type', default='webp', help='DB thumb image type')
    cmdline.add_argument('-n', '--limit', type=int, help='stop at number of processed images')
    cmdline.add_argument('--shuffle', action='store_true', help='shuffle images before processing - works best with --limit')
    # cmdline.add_argument('--verbose', action='store_true', help='show detailed logs')
    opts = cmdline.parse_args()

    if opts.move and opts.copy:
        raise ValueError('Use either move, OR copy! Cannot use both')

    if opts.limit and opts.limit < 0:
        raise ValueError('The file limit cannot be negative!')

    if opts.move:
        if not isdir(opts.move):
            raise ValueError("The output moving folder doesn't exist!")
        opts.operation = shutil.move
    elif opts.copy:
        if not isdir(opts.copy):
            raise ValueError("The output copy folder doesn't exist!")
        opts.operation = shutil.copy2
    else:
        opts.operation = None
        print('No operation was specified')

    if opts.hashes:
        # limit the size of a param, eg: --uid '{sha256:.8s}'
        opts.hashes = [f'{h.lower()}' for h in re.split('[,; ]', opts.hashes) if h]
    if opts.v_hashes:
        # explode string separated by , or ; or just space + lowerCase
        opts.v_hashes = [f'{h.lower()}' for h in re.split('[,; ]', opts.v_hashes) if h]
    if opts.exts:
        # explode string separated by , or ; or just space + lowerCase
        opts.exts = [f'.{e.lstrip(".").lower()}' for e in re.split('[,; ]', opts.exts) if e]

    if opts.db:
        # fix DB name and ext
        db_name, db_ext = os.path.splitext(opts.db)
        opts.db = db_name + (db_ext if db_ext else '.htm')

    return opts


if __name__ == '__main__':
    t0 = monotonic()
    opts = parse_args()
    main(opts)
    t1 = monotonic()
    print(f'img-DB finished in {t1-t0:.3f} sec')
