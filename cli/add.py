import argparse
import sys
from pathlib import Path

from imgdb import config
from imgdb.config import Config
from imgdb.main import add_op


def main():
    parser = argparse.ArgumentParser(prog='ImageAdd')
    parser.add_argument('inputs', nargs='+')
    parser.add_argument('-o', '--output', default='', help='import in output folder')
    parser.add_argument('--dbname', default='imgdb.htm', help='DB file name')
    parser.add_argument('--config', default='', help='optional JSON config file')
    parser.add_argument(
        '--operation', default='copy', choices=('copy', 'move', 'link'), help='import operation (copy, move, link)'
    )
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
    parser.add_argument('-f', '--filter', default='', help='filter expressions')
    parser.add_argument('--exts', default='', help='only add images with specified extensions')
    parser.add_argument('--limit', default=0, type=int, help='limit import files')
    parser.add_argument('--thumb-sz', default=96, type=int, help='DB thumb size')
    parser.add_argument('--thumb-qual', default=70, type=int, help='DB thumb quality')
    parser.add_argument('--thumb-type', default='webp', help='DB thumb type')

    parser.add_argument('--skip-imported', action='store_true', help='skip files that are already imported in the DB')
    parser.add_argument('--deep', action='store_true', help='deep search for files to process')
    parser.add_argument('--shuffle', action='store_true', help='randomize files before import')

    parser.add_argument('--dry-run', action='store_true', help="don't run, just print the operations")
    parser.add_argument('--silent', action='store_true', help='only show error logs')
    parser.add_argument('--verbose', action='store_true', help='show all logs')

    argv = sys.argv[1:]
    args = parser.parse_args(argv)
    # known, _ = parser._parse_known_args(argv, argparse.Namespace(), False)

    if not (args.output or args.dbname):
        raise ValueError('No OUTPUT or DB provided, nothing to do')
    if args.operation and not args.output and not args.dbname:
        raise ValueError(f'No OUTPUT provided for {args.operation}, nothing to do')

    dargs = vars(args)

    if args.operation and args.output:
        args.output = Path(args.output).expanduser()
    else:
        args.output = ''

    # Remove input paths from config
    inputs = [Path(f).expanduser() for f in dargs.pop('inputs')]

    cfg_path = dargs.pop('config')
    if cfg_path:  # NOQA: SIM108
        cfg = Config.from_file(cfg_path, initial=dargs)
    else:
        cfg = config.Config(**dargs)

    # Add (import) images
    add_op(inputs, cfg)


if __name__ == '__main__':
    main()
