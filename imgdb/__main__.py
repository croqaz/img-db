from pathlib import Path
from argparse import ArgumentParser
from typing import List
from PIL import Image


def parse_args():
    cmdline = ArgumentParser()
    cmdline.add_argument('files', nargs='+', type=Path)
    cmdline.add_argument('-o', '--output', default='imgdb', help='database folder')
    cmdline.add_argument('-n', '--limit', type=int, help='stop after number of items')
    cmdline.add_argument('--verbose', help='show detailed logs', action='store_true')
    opts = cmdline.parse_args()

    if opts.limit and opts.limit < 0:
        raise ValueError('The limit cannot be negative')

    return opts


def find_files(pths: List[Path]):
    to_proc = []
    for pth in pths:
        for p in pth.glob('**/*.*'):
            to_proc.append(p)
    print(f'To process: {len(to_proc)} files')
    return to_proc


def process_img(pth: str, output: str):
    try:
        img = Image.open(pth)
    except Exception as err:
        print(f'Cannot open image "{pth}"! ERROR: {err}')


if __name__ == '__main__':
    opts = parse_args()
    for f in find_files(opts.files):
        process_img(f, opts.output)
