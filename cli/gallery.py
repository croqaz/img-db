import argparse
import sys
from os.path import expanduser

from imgdb import config
from imgdb.config import Config
from imgdb.main import generate_gallery


def main():
    parser = argparse.ArgumentParser(prog='Gallery')
    parser.add_argument('name')
    parser.add_argument('--dbname', required=True, default='imgdb.htm', help='DB file name')
    parser.add_argument('--config', default='', help='optional JSON config file')
    parser.add_argument('-f', '--filter', default='', help='filter expressions')

    parser.add_argument('--tmpl', default='img_gallery.html', help='custom Jinja2 template file')
    parser.add_argument('--wrap-at', default=1000, type=int, help='create new gallery file every X images')
    parser.add_argument('--add-attrs', default='', help='pairs of attributes to add before exporting in the gallery')
    parser.add_argument('--del-attrs', default='', help='list of attributes to remove before exporting in the gallery')

    parser.add_argument('--silent', action='store_true', help='only show error logs')
    parser.add_argument('--verbose', action='store_true', help='show all logs')

    argv = sys.argv[1:]
    args = parser.parse_args(argv)
    dargs = vars(args)

    dargs['gallery'] = expanduser(dargs.pop('name'))

    cfg_path = dargs.pop('config')
    if cfg_path:  # NOQA: SIM108
        cfg = Config.from_file(cfg_path, initial=dargs)
    else:
        cfg = config.Config(**dargs)

    # Create gallery from DB
    generate_gallery(cfg)


if __name__ == '__main__':
    main()
