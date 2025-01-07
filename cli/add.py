import argparse
import asyncio
import os
import threading
import timeit
from os.path import isfile
from pathlib import Path

from imgdb import config, fsys
from imgdb.db import db_merge, db_save
from imgdb.img import img_to_meta, meta_to_html
from imgdb.log import log


async def main():
    parser = argparse.ArgumentParser(prog='ImageAdd')
    parser.add_argument('inputs', nargs='+')
    parser.add_argument('--dbname', default='imgdb.htm', help='DB file name')
    parser.add_argument('--operation', default='copy', help='import operation (copy, move, link)')
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
    parser.add_argument('--limit', default=0, type=int, help='limit import files')
    parser.add_argument('--thumb-sz', default=96, type=int, help='DB thumb size')
    parser.add_argument('--thumb-qual', default=70, type=int, help='DB thumb quality')
    parser.add_argument('--thumb-type', default='webp', help='DB thumb type')
    parser.add_argument('--deep', action='store_true', help='deep search for files')
    parser.add_argument('--shuffle', action='store_true', help='randomize files before import')

    args = parser.parse_args()
    file_start = timeit.default_timer()

    dargs = vars(args)
    inputs = [Path(f).expanduser() for f in dargs.pop('inputs')]
    cfg = config.Config(**dargs)
    files = fsys.find_files(inputs, cfg)
    del inputs

    stream = None
    if args.dbname:
        dbname = cfg.dbname
        log.debug(f'Using DB file "{dbname}"')
        if not isfile(dbname):
            with open(dbname, 'w') as fd:
                fd.write('<!DOCTYPE html>')
        # open with append + read
        stream = open(dbname + '~', 'a+')  # noqa

    semaphore = asyncio.Semaphore(4)
    stream_lock = threading.Lock()

    async def _add_img(p: Path):
        async with semaphore:
            img, m = img_to_meta(p, cfg)
            if not (img and m):
                return
        if stream:
            with stream_lock:
                stream.write(meta_to_html(m, cfg))
        return m

    await asyncio.gather(*map(_add_img, files))

    if stream:
        # consolidate DB!
        stream.seek(0)
        stream_txt = stream.read()
        stream.close()
        if stream_txt:
            # the stream must be the second arg,
            # so it will overwrite the existing DB
            t = db_merge(
                open(dbname, 'r').read(),  # noqa
                stream_txt,
            )
            db_save(t, dbname)
        os.remove(stream.name)
        # force write everything
        os.sync()

    file_stop = timeit.default_timer()
    log.debug(f'[{len(files)}] files processed in {(file_stop - file_start):.4f}s')


if __name__ == '__main__':
    asyncio.run(main())
