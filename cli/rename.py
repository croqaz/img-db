import argparse
import sys
from pathlib import Path

from imgdb.config import Config
from imgdb.main import rename


def main():
    parser = argparse.ArgumentParser(prog='ImageRename')
    parser.add_argument('inputs', nargs='+')
    parser.add_argument('--name', required=True, help='base name used to rename all imgs')
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
    parser.add_argument('--exts', default='', help='only add images with specified extensions')
    parser.add_argument('--limit', default=0, type=int, help='limit rename files')

    parser.add_argument('--force', action='store_true', help='force overwrite existing files')
    parser.add_argument('--deep', action='store_true', help='deep search for files to process')
    parser.add_argument('--shuffle', action='store_true', help='randomize files before rename')

    parser.add_argument('--dry-run', action='store_true', help="don't run, just print the operations")
    parser.add_argument('--silent', action='store_true', help='only show error logs')
    parser.add_argument('--verbose', action='store_true', help='show all logs')

    argv = sys.argv[1:]
    args = parser.parse_args(argv)
    dargs = vars(args)

    if not len(args.inputs):
        raise ValueError('Must provide at least one INPUT folder')

    cfg = Config(
        c_hashes=args.c_hashes,
        v_hashes=args.v_hashes,
        metadata=args.metadata,
        exts=args.exts,
        limit=args.limit,
        deep=args.deep,
        force=args.force,
        shuffle=args.shuffle,
        dry_run=args.dry_run,
        silent=args.silent,
        verbose=args.verbose,
    )

    inputs = [Path(f).expanduser() for f in dargs.pop('inputs')]
    rename(inputs, args.name, cfg)


if __name__ == '__main__':
    main()
