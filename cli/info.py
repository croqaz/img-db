import argparse
import timeit
from pathlib import Path

from imgdb import config, img


def main():
    parser = argparse.ArgumentParser(prog='ImageInfo')
    parser.add_argument('inputs', nargs='+')
    parser.add_argument(
        '--c-hashes',
        default='blake2b',
        help='cryptographical hashes (separated by space or comma)',
    )
    parser.add_argument(
        '--v-hashes',
        default='dhash',
        help='visual hashes (separated by space or comma)',
    )
    parser.add_argument(
        '--metadata', default='', help='extra metadata (shutter-speed, aperture, iso, orientation, etc)'
    )
    parser.add_argument(
        '--algorithms',
        default='',
        help='extra algorithms to run (top colors, average color, etc)',
    )
    parser.add_argument('--thumb-sz', default=96, type=int, help='DB thumb size')
    parser.add_argument('--thumb-qual', default=70, type=int, help='DB thumb quality')
    parser.add_argument('--thumb-type', default='webp', help='DB thumb type')
    args = parser.parse_args()
    cfg = config.Config(**vars(args))

    file_start = timeit.default_timer()

    for in_file in args.inputs:
        pth = Path(in_file)
        im, nfo = img.img_to_meta(pth, cfg)
        del nfo['__e']
        print(nfo)

    file_stop = timeit.default_timer()
    print(f'[{len(args.inputs)}] files processed in {(file_stop - file_start):.4f}s')


if __name__ == '__main__':
    main()
