import re
import shutil
from argparse import ArgumentParser
from time import monotonic
from os.path import isdir
from pathlib import Path

from .main import find_files, img_meta, img_archive
from .img import export_img_details_html


def parse_args():
    cmdline = ArgumentParser()
    cmdline.add_argument('folders', nargs='+', type=Path)
    cmdline.add_argument('--move', help='move in the database folder')
    cmdline.add_argument('--copy', help='copy in the database folder')
    cmdline.add_argument('--naming', default='dhash', help='the naming function: dhash, SHA256, BLAKE2b')
    cmdline.add_argument('--exts', help='filter by extension: eg: JPG, PNG, etc')
    cmdline.add_argument('-n', '--limit', type=int, help='stop at number of processed images')
    cmdline.add_argument('--verbose', help='show detailed logs', action='store_true')
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

    if opts.exts:
        # explode string separated by , or ; or just space
        opts.exts = [f'.{e.lower()}' for e in re.split('[,; ]', opts.exts) if e]

    return opts


if __name__ == '__main__':
    t0 = monotonic()
    opts = parse_args()

    metas = []

    for f in find_files(opts.folders, opts):
        img, m = img_meta(f, opts)
        if not (img and m):
            continue
        metas.append((img, m))
        if opts.operation:
            img_archive(m, opts)

    export_img_details_html(metas)

    t1 = monotonic()
    print(f'img-DB finished in {t1-t0:.3f} sec')
