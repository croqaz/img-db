import argparse

from imgdb.config import Config
from imgdb.main import info


def handle_info():
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
    parser.add_argument('--silent', action='store_true', help='only show error logs')
    parser.add_argument('--verbose', action='store_true', help='show all logs')

    args = parser.parse_args()
    dargs = vars(args)
    inputs = dargs.pop('inputs')
    cfg = Config(**dargs)
    info(inputs, cfg)


if __name__ == '__main__':
    handle_info()
