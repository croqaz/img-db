import argparse
import sys

from imgdb import config
from imgdb.main import del_op


def handle_del():
    parser = argparse.ArgumentParser(prog='ImageDel')
    parser.add_argument('--names', nargs='+')
    parser.add_argument('--dbname', default='imgdb.htm', help='DB file name')

    parser.add_argument('-f', '--filter', default='', help='filter expressions')
    parser.add_argument('--exts', default='', help='only add images with specified extensions')
    parser.add_argument('--limit', default=0, type=int, help='limit import files')

    parser.add_argument('--dry-run', action='store_true', help="don't run, just print the operations")
    parser.add_argument('--silent', action='store_true', help='only show error logs')
    parser.add_argument('--verbose', action='store_true', help='show all logs')

    argv = sys.argv[1:]
    args = parser.parse_args(argv)
    dargs = vars(args)

    names = dargs.pop('names')
    dargs = vars(args)
    cfg = config.Config(**dargs)

    # Delete images from DB and archive
    del_op(names, cfg)


if __name__ == '__main__':
    handle_del()
