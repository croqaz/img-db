import shutil
from argparse import ArgumentParser
from time import monotonic
from os.path import isdir
from pathlib import Path
from typing import List

from .img import img_meta, img_archive


def parse_args():
    cmdline = ArgumentParser()
    cmdline.add_argument('folders', nargs='+', type=Path)
    cmdline.add_argument('--move', help='move in the database folder')
    cmdline.add_argument('--copy', help='copy in the database folder')
    cmdline.add_argument('--naming', default='dhash', help='the naming function: dhash, SHA256, BLAKE2b')
    cmdline.add_argument('--index-only', action='store_true', help="don't move or copy, just index")
    cmdline.add_argument('-n', '--limit', type=int, help='stop at number of processed images')
    cmdline.add_argument('--verbose', help='show detailed logs', action='store_true')
    opts = cmdline.parse_args()

    if opts.index_only and (opts.move or opts.copy):
        raise ValueError('Use either index-only, OR move/copy!')

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

    return opts


def find_files(folders: List[Path], limit=0):
    to_proc = []
    index = 1
    for pth in folders:
        if not pth.is_dir():
            print(f'Path "{pth}" is not a folder!')
            continue
        for p in pth.glob('**/*.*'):
            to_proc.append(p)
            if limit > 0:
                index += 1
                if index > limit:
                    print(f'To process: {len(to_proc)} files')
                    return to_proc
    print(f'To process: {len(to_proc)} files')
    return to_proc


if __name__ == '__main__':
    t0 = monotonic()
    opts = parse_args()

    for f in find_files(opts.folders, opts.limit):
        m = img_meta(f)
        if not opts.operation:
            print('META:', m)
        else:
            img_archive(m, opts)

    t1 = monotonic()
    print(f'img-DB finished in {t1-t0:.3f} sec')
