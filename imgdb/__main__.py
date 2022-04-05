import os
import re
import click
import shutil
from argparse import ArgumentParser, Namespace
from os.path import isdir
from pathlib import Path

from .config import Config
from .db import db_open, db_query
from .gallery import generate_gallery
from .link import generate_links
from .log import log


@click.group(help='img-DB cli app')
@click.pass_context
def cli(ctx):
    pass


@cli.command()
@click.option('--db', default='imgdb.htm', type=click.Path(exists=True))
@click.option('-f', '--filter', help='a filter expression query')
@click.option('-e', '--exts', default='', help='filter by extension, eg: JPG, PNG, etc')
@click.option('-n', '--limit', default=0, help='stop at number of processed images')
@click.option('-v', '--verbose', is_flag=True, help='show detailed logs')
@click.argument('name')
def links(db, filter, exts, limit, verbose, name):
    if verbose:
        log.setLevel(10)
    c = Config(links=name, dbname=db, filter=filter, exts=exts, limit=limit, verbose=verbose)
    c.db = db_open(db)
    return generate_links(c.db, c)


@cli.command()
@click.option('--db', default='imgdb.htm', type=click.Path(exists=True))
@click.option('-f', '--filter', help='a filter expression query')
@click.option('-e', '--exts', default='', help='filter by extension, eg: JPG, PNG, etc')
@click.option('-n', '--limit', default=0, help='stop at number of processed images')
@click.option('-v', '--verbose', is_flag=True, help='show detailed logs')
@click.argument('name')
def gallery(db, filter, exts, limit, verbose, name):
    if verbose:
        log.setLevel(10)
    c = Config(gallery=name, dbname=db, filter=filter, exts=exts, limit=limit, verbose=verbose)
    c.db = db_open(db)
    return generate_gallery(c.db, c)


@cli.command()
def add():
    print('WILL ADD THINGS')


@cli.group('db')
@click.option('-n', '--name', default='imgdb.htm', show_default=True)
@click.option('-q', '--query', default='', help='a filter expression query')
@click.option('-v', '--verbose', is_flag=True, help='show detailed logs')
@click.pass_context
def cli_db(ctx, name, query, verbose):
    ctx.obj = Config(dbname=name, filter=query, verbose=verbose)
    ctx.obj.db = db_open(name)


@cli_db.command('debug', short_help='interactive DB commands')
@click.pass_obj
def cli_db_debug(cfg):
    return db_query(cfg.db, cfg)


def parse_args(args=None) -> Namespace:
    cmdline = ArgumentParser()
    cmdline.add_argument('folders', nargs='+', type=Path)
    cmdline.add_argument('--db', help='DB/cache file location')
    cmdline.add_argument('--query', action='store_true', help='DB/cache query')
    cmdline.add_argument('--move', help='move in the database folder')
    cmdline.add_argument('--copy', help='copy in the database folder')
    cmdline.add_argument('--gallery', help='generate gallery with template')
    cmdline.add_argument('--links', help='generate links with template')
    cmdline.add_argument('--sym-links', action='store_true', help='sym-links')
    cmdline.add_argument('--uid',
                         default='{blake2b}',
                         help='the UID is used to calculate the uniqueness of the img, BE VERY CAREFUL')
    cmdline.add_argument('--filter', help='only filter images that match specified RE pattern')
    cmdline.add_argument('--hashes', default='blake2b', help='content hashing, eg: BLAKE2b, SHA256, etc')
    cmdline.add_argument('--v-hashes', default='dhash', help='perceptual hashing (ahash, dhash, vhash, phash)')
    cmdline.add_argument('--metadata', help='extra metadata (shutter-speed, aperture, iso, orientation)')
    cmdline.add_argument('--exts', help='filter by extension, eg: JPG, PNG, etc')
    cmdline.add_argument('--ignore-sz', type=int, default=128, help='ignore images smaller than')
    cmdline.add_argument('--thumb-sz', type=int, default=128, help='DB thumb size')
    cmdline.add_argument('--thumb-qual', type=int, default=70, help='DB thumb quality')
    cmdline.add_argument('--thumb-type', default='webp', help='DB thumb image type')
    cmdline.add_argument('-n', '--limit', type=int, help='stop at number of processed images')
    cmdline.add_argument('--shuffle',
                         action='store_true',
                         help='shuffle images before processing - works best with --limit')
    cmdline.add_argument('--force', action='store_true', help='apply force')
    cmdline.add_argument('--verbose', action='store_true', help='show detailed logs')
    opts = cmdline.parse_args(args)

    if opts.verbose:
        log.setLevel(10)

    if opts.move and opts.copy:
        raise ValueError('Use either move, OR copy! Cannot use both')

    if opts.limit and opts.limit < 0:
        raise ValueError('The file limit cannot be negative!')

    if opts.move:
        if not isdir(opts.move):
            raise ValueError("The output moving folder doesn't exist!")
        opts.operation = shutil.move
    elif opts.copy:
        if not isdir(opts.copy):
            raise ValueError("The output copy folder doesn't exist!")
        opts.operation = shutil.copy2
    else:
        opts.operation = None
        log.debug('No operation was specified')

    if opts.hashes:
        # limit the size of a param, eg: --uid '{sha256:.8s}'
        opts.hashes = [f'{h.lower()}' for h in re.split('[,; ]', opts.hashes) if h]
    if opts.v_hashes:
        if opts.v_hashes == '*':
            opts.v_hashes = sorted(VHASHES)
        else:
            # explode string separated by , or ; or just space + lowerCase
            opts.v_hashes = [f'{v.lower()}' for v in re.split('[,; ]', opts.v_hashes) if v]
    if opts.metadata:
        # explode string separated by , or ; or just space + lowerCase
        opts.metadata = [f'{v.lower()}' for v in re.split('[,; ]', opts.metadata) if v]
    if opts.exts:
        # explode string separated by , or ; or just space + lowerCase
        opts.exts = [f'.{e.lstrip(".").lower()}' for e in re.split('[,; ]', opts.exts) if e]

    if opts.db:
        # fix DB name and ext
        db_name, db_ext = os.path.splitext(opts.db)
        opts.db = db_name + (db_ext if db_ext else '.htm')

    return opts


if __name__ == '__main__':
    # t0 = monotonic()
    # main(parse_args())
    # t1 = monotonic()
    # log.info(f'img-DB finished in {t1-t0:.3f} sec')
    cli(obj={})
