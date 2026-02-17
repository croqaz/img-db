import argparse
from multiprocessing import freeze_support
from os.path import expanduser
from pathlib import Path

import uvicorn

from imgdb import config
from imgdb.config import Config
from imgdb.main import add_op, db_op, del_op, generate_gallery, generate_links, info, ren_op
from imgdb.server.run import app


def main(argv: list[str] | None = None):  # pragma: no cover
    parser = argparse.ArgumentParser(prog='imgdb')
    subparsers = parser.add_subparsers(dest='cmd', required=True, help='sub-command to run')

    # --- INFO ---
    p_info = subparsers.add_parser('info', help='show image info')
    p_info.add_argument('inputs', nargs='+')
    p_info.add_argument('--c-hashes', default='blake2b', help='cryptographic hashes (separated by space or comma)')
    p_info.add_argument('--v-hashes', default='dhash', help='visual hashes (separated by space or comma)')
    p_info.add_argument(
        '--metadata', default='', help='extra metadata (shutter-speed, aperture, iso, orientation, etc)'
    )
    p_info.add_argument('--algorithms', default='', help='extra algorithms to run (top-colors, illumination, etc)')
    p_info.add_argument('--silent', action='store_true', help='only show error logs')
    p_info.add_argument('--verbose', action='store_true', help='show all logs')

    # --- SERVER ---
    p_server = subparsers.add_parser('server', help='run the web server')
    p_server.add_argument('--host', default='127.0.0.1', help='server host')
    p_server.add_argument('--port', default=18888, type=int, help='server port')
    p_server.add_argument('--workers', default=1, type=int, help='number of workers')
    p_server.add_argument('--silent', action='store_true', help='only show error logs')
    p_server.add_argument('--verbose', action='store_true', help='show all logs')

    # --- ADD ---
    p_add = subparsers.add_parser('add', help='add (import) images')
    p_add.add_argument('inputs', nargs='+')
    p_add.add_argument('-o', '--output', default='', help='import in output folder')
    p_add.add_argument('--db', default='imgdb.htm', help='DB file name')
    p_add.add_argument('--config', default='', help='optional JSON config file')
    p_add.add_argument(
        '--operation',
        default='noop',
        choices=('noop', 'copy', 'move', 'link'),
        help='import operation (noop, copy, move, link)',
    )
    p_add.add_argument('--c-hashes', default='blake2b', help='cryptographic hashes (separated by space or comma)')
    p_add.add_argument('--v-hashes', default='dhash', help='visual hashes (separated by space or comma)')
    p_add.add_argument('--metadata', default='', help='extra metadata (shutter-speed, aperture, iso, orientation, etc)')
    p_add.add_argument('--algorithms', default='', help='extra algorithms to run (top-colors, illumination, etc)')
    p_add.add_argument('-f', '--filter', default='', help='filter expressions')
    p_add.add_argument('--exts', default='', help='only add images with specified extensions')
    p_add.add_argument('--limit', default=0, type=int, help='limit imported files')
    p_add.add_argument('--thumb-sz', default=96, type=int, help='DB thumb size')
    p_add.add_argument('--thumb-qual', default=70, type=int, help='DB thumb quality')
    p_add.add_argument('--thumb-type', default='webp', help='DB thumb type')
    p_add.add_argument('--skip-imported', action='store_true', help='skip files that are already imported in the DB')
    p_add.add_argument('--deep', action='store_true', help='deep (recursive) search for files to import')
    p_add.add_argument('--shuffle', action='store_true', help='randomize files before import')
    p_add.add_argument('--dry-run', action='store_true', help="don't run, just print the operations")
    p_add.add_argument('--silent', action='store_true', help='only show error logs')
    p_add.add_argument('--verbose', action='store_true', help='show all logs')

    # --- DEL ---
    p_del = subparsers.add_parser('del', help='delete images')
    p_del.add_argument('--names', nargs='+')
    p_del.add_argument('--db', default='imgdb.htm', help='DB file name')
    p_del.add_argument('-f', '--filter', default='', help='filter expressions')
    p_del.add_argument('--exts', default='', help='only del images with specified extensions')
    p_del.add_argument('--limit', default=0, type=int, help='limit deleted files')
    p_del.add_argument('--dry-run', action='store_true', help="don't run, just print the operations")
    p_del.add_argument('--silent', action='store_true', help='only show error logs')
    p_del.add_argument('--verbose', action='store_true', help='show all logs')

    # --- GALLERY ---
    p_gallery = subparsers.add_parser('gallery', help='create gallery from DB')
    p_gallery.add_argument('name')
    p_gallery.add_argument('--db', required=True, default='imgdb.htm', help='DB file name')
    p_gallery.add_argument('--config', default='', help='optional JSON config file')
    p_gallery.add_argument('-f', '--filter', default='', help='filter expressions')
    p_gallery.add_argument('--tmpl', default='img_gallery.html', help='custom Jinja2 template file')
    p_gallery.add_argument('--wrap-at', default=1000, type=int, help='create new gallery file every X images')
    p_gallery.add_argument('--add-attrs', default='', help='pairs of attributes to add before exporting in the gallery')
    p_gallery.add_argument(
        '--del-attrs', default='', help='list of attributes to remove before exporting in the gallery'
    )
    p_gallery.add_argument('--silent', action='store_true', help='only show error logs')
    p_gallery.add_argument('--verbose', action='store_true', help='show all logs')

    # --- LINKS ---
    p_links = subparsers.add_parser('links', help='create links from DB')
    p_links.add_argument('name')
    p_links.add_argument('--db', default='imgdb.htm', help='DB file name')
    p_links.add_argument('--config', default='', help='optional JSON config file')
    p_links.add_argument('-f', '--filter', default='', help='filter expressions')
    p_links.add_argument('--sym-links', action='store_true', help='use sym-links (soft links) instead or hard-links')
    p_links.add_argument('--exts', default='', help='only link images with specified extensions')
    p_links.add_argument('--limit', default=0, type=int, help='limit linking files')
    p_links.add_argument('--force', action='store_true', help='force overwrite existing files')
    p_links.add_argument('--silent', action='store_true', help='only show error logs')
    p_links.add_argument('--verbose', action='store_true', help='show all logs')

    # --- DB ---
    p_db = subparsers.add_parser('db', help='run DB operations')
    p_db.add_argument('op', help='operation name')
    p_db.add_argument('--db', required=True, default='imgdb.htm', help='DB file name')
    p_db.add_argument('--config', default='', help='optional JSON config file')
    p_db.add_argument('--output', default='', help='DB export output')
    p_db.add_argument('--format', default='jl', help='DB export format')
    p_db.add_argument('-f', '--filter', default='', help='filter expressions')
    p_db.add_argument('--silent', action='store_true', help='only show error logs')
    p_db.add_argument('--verbose', action='store_true', help='show all logs')

    # --- RENAME ---
    p_rename = subparsers.add_parser('rename', help='rename images in the input folder(s)')
    p_rename.add_argument('inputs', nargs='+')
    p_rename.add_argument('--name', required=True, help='base name used to rename all images')
    p_rename.add_argument('--c-hashes', default='blake2b', help='cryptographic hashes (separated by space or comma)')
    p_rename.add_argument('--v-hashes', default='dhash', help='visual hashes (separated by space or comma)')
    p_rename.add_argument(
        '--metadata', default='', help='extra metadata (shutter-speed, aperture, iso, orientation, etc)'
    )
    p_rename.add_argument('--exts', default='', help='only use images with specified extensions')
    p_rename.add_argument('--limit', default=0, type=int, help='limit renamed files')
    p_rename.add_argument('--force', action='store_true', help='force overwrite existing files')
    p_rename.add_argument('--deep', action='store_true', help='deep (recursive) search for files to rename')
    p_rename.add_argument('--shuffle', action='store_true', help='randomize files before rename')
    p_rename.add_argument('--dry-run', action='store_true', help="don't run, just print the operations")
    p_rename.add_argument('--silent', action='store_true', help='only show error logs')
    p_rename.add_argument('--verbose', action='store_true', help='show all logs')

    args = parser.parse_args(argv)
    vargs = vars(args)
    cmd = vargs.pop('cmd')

    if cmd == 'info':
        inputs = vargs.pop('inputs')
        cfg = Config(**vargs)
        info(inputs, cfg)

    elif cmd == 'server':
        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            workers=args.workers,
            log_level='warning' if args.silent else 'info',
        )

    elif cmd == 'add':
        if not (args.output or args.db):
            raise ValueError('No OUTPUT or DB provided, nothing to do')
        if args.operation and not args.output and not args.db:
            raise ValueError(f'No OUTPUT provided for {args.operation}, nothing to do')

        if args.operation and args.output:
            vargs['output'] = Path(args.output).expanduser()
        else:
            vargs['output'] = ''

        inputs = [Path(f).expanduser() for f in vargs.pop('inputs')]
        cfg_path = vargs.pop('config')
        if cfg_path:  # NOQA: SIM108
            cfg = Config.from_file(cfg_path, initial=vargs)
        else:
            cfg = config.Config(**vargs)

        # Add (import) images
        add_op(inputs, cfg)

    elif cmd == 'del':
        names = vargs.pop('names')
        cfg = config.Config(**vargs)
        # Delete images from DB and archive
        del_op(names, cfg)

    elif cmd == 'gallery':
        vargs['gallery'] = expanduser(vargs.pop('name'))
        cfg_path = vargs.pop('config')
        if cfg_path:  # NOQA: SIM108
            cfg = Config.from_file(cfg_path, initial=vargs)
        else:
            cfg = config.Config(**vargs)
        generate_gallery(cfg)

    elif cmd == 'links':
        vargs['links'] = expanduser(vargs.pop('name'))
        cfg_path = vargs.pop('config')
        if cfg_path:  # NOQA: SIM108
            cfg = Config.from_file(cfg_path, initial=vargs)
        else:
            cfg = config.Config(**vargs)
        generate_links(cfg)

    elif cmd == 'db':
        if args.output and args.format:
            vargs['output'] = Path(args.output).expanduser()
        operation_name = vargs.pop('op')
        cfg_path = vargs.pop('config')
        if cfg_path:  # NOQA: SIM108
            cfg = Config.from_file(cfg_path, initial=vargs)
        else:
            cfg = config.Config(**vargs)
        # Start DB operations
        db_op(operation_name, cfg)

    elif cmd == 'rename':
        if not len(args.inputs):
            raise ValueError('Must provide at least one INPUT folder')
        inputs = [Path(f).expanduser() for f in vargs.pop('inputs')]
        rename_name = vargs.pop('name')
        cfg = config.Config(**vargs)
        ren_op(inputs, rename_name, cfg)


if __name__ == '__main__':
    # Required for PyInstaller and multiprocessing
    freeze_support()
    main()
