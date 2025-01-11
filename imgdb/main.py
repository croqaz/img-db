"""
High level functions, usable as a library.
They are imported in CLI and GUI.
"""

import os
import timeit
from multiprocessing import Process, Queue, cpu_count
from os.path import isfile
from pathlib import Path

from .config import Config
from .db import db_merge, db_open, db_save
from .fsys import find_files
from .img import img_archive, img_to_meta, meta_to_html
from .log import log


def info(inputs: list, cfg: Config):
    file_start = timeit.default_timer()

    for in_file in inputs:
        pth = Path(in_file)
        im, nfo = img_to_meta(pth, cfg)
        del nfo['__e']
        print(nfo)

    file_stop = timeit.default_timer()
    log.debug(f'[{len(inputs)}] files processed in {(file_stop - file_start):.4f}s')


def add_worker(image_queue: Queue, result_queue: Queue, c: Config):
    for img_path in iter(image_queue.get, 'STOP'):
        if img_path == 'STOP':
            break
        img, m = img_to_meta(img_path, c)
        if img and m:
            result_queue.put(m)
        else:
            result_queue.put({})


def add(inputs: list, cfg: Config):
    file_start = timeit.default_timer()
    files = find_files(inputs, cfg)

    stream = None
    if cfg.dbname:
        dbname = cfg.dbname
        log.debug(f'Using DB file "{dbname}"')
        if not isfile(dbname):
            with open(dbname, 'w') as fd:
                fd.write('<!DOCTYPE html>')
        # open with append + read
        stream = open(dbname + '~', 'a+')  # noqa

    image_queue = Queue()
    result_queue = Queue()
    workers = []

    for img_path in files:
        image_queue.put(img_path)

    # Create workers for each CPU core
    cpus = cpu_count()
    for _ in range(cpus):
        p = Process(target=add_worker, args=(image_queue, result_queue, cfg))
        workers.append(p)
        p.start()

    # Signal workers to stop by adding 'STOP' into the queue
    for _ in range(cpus):
        image_queue.put('STOP')

    batch = []
    batch_size = cpus * 2
    processed_count = 0
    existing = {el['id'] for el in db_open(cfg.dbname).find_all('img')}

    while processed_count < len(files):
        result = result_queue.get()
        processed_count += 1
        batch.append(result)

        # Process batch when it reaches the batch size or when all images are processed
        if len(batch) == batch_size or processed_count == len(files):
            for m in batch:
                if not m:
                    continue
                if cfg.skip_imported and m['id'] in existing:
                    log.debug(f'skip imported {m["pth"]}')
                    continue
                if cfg.archive and cfg.add_func:
                    img_archive(m, cfg)
                elif m['id'] in existing:
                    log.debug(f'update DB: {m["pth"]}')
                else:
                    log.debug(f'to DB: {m["pth"]}')
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
