import argparse
import os
import timeit
from multiprocessing import Process, Queue, cpu_count
from os.path import isfile
from pathlib import Path

from imgdb import config, fsys
from imgdb.db import db_merge, db_save
from imgdb.img import img_to_meta, meta_to_html
from imgdb.log import log


def main():
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
    add(args)


def worker(image_queue: Queue, result_queue: Queue, c: config.Config):
    for img_path in iter(image_queue.get, 'STOP'):
        if img_path == 'STOP':
            break
        img, m = img_to_meta(img_path, c)
        if img and m:
            result_queue.put(m)
        else:
            result_queue.put({})


def add(args):
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

    image_queue = Queue()
    result_queue = Queue()
    cpus = cpu_count()
    workers = []

    for img_path in files:
        image_queue.put(img_path)

    # Create workers for each CPU core
    for _ in range(cpus):
        p = Process(target=worker, args=(image_queue, result_queue, cfg))
        workers.append(p)
        p.start()

    # Signal workers to stop by adding 'STOP' into the queue
    for _ in range(cpus):
        image_queue.put('STOP')

    batch = []
    batch_size = cpus * 2
    processed_count = 0

    while processed_count < len(files):
        result = result_queue.get()
        processed_count += 1
        batch.append(result)

        # Process batch when it reaches the batch size or when all images are processed
        if len(batch) == batch_size or processed_count == len(files):
            for m in batch:
                if not m:
                    continue
                if stream:
                    stream.write(meta_to_html(m, cfg))
            batch = []

    # Wait for all workers to complete
    for p in workers:
        p.join()

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
    main()
