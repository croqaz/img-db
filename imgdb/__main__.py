from pathlib import Path
from argparse import ArgumentParser
from typing import List
from PIL import Image

from .naming import content_hash_img, perc_hash_img


def parse_args():
    cmdline = ArgumentParser()
    cmdline.add_argument('folders', nargs='+', type=Path)
    cmdline.add_argument('-o', '--output', default='imgdb', help='database folder')
    cmdline.add_argument('-n', '--limit', type=int, help='stop after number of items')
    cmdline.add_argument('--verbose', help='show detailed logs', action='store_true')
    opts = cmdline.parse_args()

    if opts.limit and opts.limit < 0:
        raise ValueError('The limit cannot be negative')

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
            if limit:
                index += 1
                if index > limit:
                    print(f'To process: {len(to_proc)} files')
                    return to_proc
    print(f'To process: {len(to_proc)} files')
    return to_proc


def process_img(pth: str, output: str):
    try:
        img = Image.open(pth)
    except Exception as err:
        print(f"Cannot open image '{pth}'! ERROR: {err}")
        return
    # print(content_hash_img(pth))
    # print(perc_hash_img(img))


if __name__ == '__main__':
    opts = parse_args()
    for f in find_files(opts.folders, opts.limit):
        process_img(f, opts.output)
