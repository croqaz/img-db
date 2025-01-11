"""
High level functions, usable as a library.
They are imported in CLI and GUI.
"""

import os
import timeit
from datetime import datetime
from multiprocessing import Process, Queue, cpu_count
from os import rename as os_rename
from os.path import isfile, split, splitext
from pathlib import Path

from .config import IMG_DATE_FMT, Config
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
    """Add (import) images."""
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


def readd(
    archive: str,
    # uid: str = '{blake2b}', # option disabled for now
    config: str = '',
    c_hashes='blake2b',
    v_hashes='dhash',
    metadata='',
    algorithms='',
    exts: str = '',
    limit: int = 0,
    thumb_sz: int = 96,
    thumb_qual: int = 70,
    thumb_type: str = 'webp',
    dbname: str = 'imgdb.htm',
    shuffle: bool = False,
    silent: bool = False,
    verbose: bool = False,
):
    """This is a IRREVERSIBLE rename operation, be CAREFUL!
    Be extra careful if changing the default UID flag, because you CAN OVERWRITE and LOSE your images!
    This will rename and move all the images from the archive folder,
    back into the archive folder, but with different names depending on the hash and UID.
    This is useful to normalize your DB, if you want all your images to have the same thumb size,
    same hashes, same visual hashes, same metadata.
    Also useful if the already imported images don't have enough props, maybe you want to calculate
    all the visual-hashes for all the images.
    It's also possible that some images from the archive don't have the same hash anymore,
    because they were edited, eg: resized, cropped, auto-colors, auto-levels.
    """
    add(
        archive,
        config=config,
        operation='move',
        archive=archive,
        c_hashes=c_hashes,
        v_hashes=v_hashes,
        metadata=metadata,
        algorithms=algorithms,
        exts=exts,
        limit=limit,
        thumb_sz=thumb_sz,
        thumb_qual=thumb_qual,
        thumb_type=thumb_type,
        dbname=dbname,
        deep=True,
        force=True,
        shuffle=shuffle,
        silent=silent,
        verbose=verbose,
    )


def rename(
    inputs: str,
    name: str,  # the base name used to rename all imgs
    cfg: Config,
):
    """Rename and move matching images into output folder.
    This operation doesn't use a DB or config.
    """
    for fname in find_files(inputs, cfg):
        img, m = img_to_meta(fname, cfg)
        if not (img and m):
            continue

        # it's useful to have more native objects available
        m['Pth'] = Path(m['pth'])
        if m['date']:
            m['Date'] = datetime.strptime(m['date'], IMG_DATE_FMT)
        else:
            m['Date'] = datetime(1900, 1, 1, 0, 0, 0)

        folder, old_name_ext = split(fname)
        old_name, ext = splitext(old_name_ext)
        # normalize exts
        ext = ext.lower()
        # normalize JPEG
        if ext == '.jpeg':
            ext = '.jpg'

        new_base_name = eval(f'f"""{name}"""', dict(m))
        if new_base_name == old_name:
            continue

        new_name = new_base_name + ext
        new_file = f'{folder}/{new_name}'
        if isfile(new_file) and not cfg.force:
            log.debug(f'skipping rename of {old_name_ext}, because {new_name} exists')
            continue

        try:
            os_rename(fname, new_file)
            log.debug(f'rename: {old_name_ext}  ->  {new_name}')
        except Exception as err:
            log.warn(f'Cannot rename {old_name_ext} -> {new_name} ! Err: {err}')
