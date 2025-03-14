import argparse
import sys
from os.path import expanduser

from imgdb import config
from imgdb.config import Config
from imgdb.main import generate_links


def main():
    parser = argparse.ArgumentParser(prog='Links')
    parser.add_argument('name')
    parser.add_argument('--dbname', default='imgdb.htm', help='DB file name')
    parser.add_argument('--config', default='', help='optional JSON config file')
    parser.add_argument('-f', '--filter', default='', help='filter expressions')

    parser.add_argument('--sym-links', action='store_true', help='use sym-links (soft links) instead or hard-links')
    parser.add_argument('--exts', default='', help='only link images with specified extensions')
    parser.add_argument('--limit', default=0, type=int, help='limit linking files')

    parser.add_argument('--force', action='store_true', help='force overwrite existing files')
    parser.add_argument('--silent', action='store_true', help='only show error logs')
    parser.add_argument('--verbose', action='store_true', help='show all logs')

    argv = sys.argv[1:]
    args = parser.parse_args(argv)
    dargs = vars(args)

    dargs['links'] = expanduser(dargs.pop('name'))

    cfg_path = dargs.pop('config')
    if cfg_path:  # NOQA: SIM108
        cfg = Config.from_file(cfg_path, initial=dargs)
    else:
        cfg = config.Config(**dargs)

    # Create links from archive
    generate_links(cfg)


if __name__ == '__main__':
    main()
