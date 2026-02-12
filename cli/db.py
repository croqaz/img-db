import argparse
import sys
from pathlib import Path

from imgdb import config
from imgdb.config import Config
from imgdb.main import db_op


def handle_db():
    parser = argparse.ArgumentParser(prog='DB-Operations')
    parser.add_argument('op', help='operation name')
    parser.add_argument('--dbname', required=True, default='imgdb.htm', help='DB file name')
    parser.add_argument('--config', default='', help='optional JSON config file')
    parser.add_argument('--output', default='', help='DB export output')
    parser.add_argument('--format', default='jl', help='DB export format')
    parser.add_argument('-f', '--filter', default='', help='filter expressions')
    parser.add_argument('--silent', action='store_true', help='only show error logs')
    parser.add_argument('--verbose', action='store_true', help='show all logs')

    argv = sys.argv[1:]
    args = parser.parse_args(argv)

    if args.output and args.format:
        args.output = Path(args.output).expanduser()

    dargs = vars(args)
    operation_name = dargs.pop('op')

    cfg_path = dargs.pop('config')
    if cfg_path:  # NOQA: SIM108
        cfg = Config.from_file(cfg_path, initial=dargs)
    else:
        cfg = config.Config(**dargs)

    # Start DB operations
    db_op(operation_name, cfg)


if __name__ == '__main__':
    handle_db()
