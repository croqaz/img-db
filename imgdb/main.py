"""
High level functions, usable as a library.
They are imported in CLI and GUI.
"""

import os
import timeit
from datetime import datetime
from multiprocessing import Process, Queue, cpu_count
from os.path import isfile, split, splitext
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from tqdm import tqdm

from .config import IMG_DATE_FMT, Config
from .db import db_filter, db_merge, db_open, db_save
from .fsys import find_files
from .img import img_archive, img_to_meta, meta_to_html
from .log import log
from .util import slugify


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
            log.debug(f'rename: {old_name_ext}  ->  {new_name}')
            os.rename(fname, new_file)
        except Exception as err:
            log.warn(f'Cannot rename {old_name_ext} -> {new_name} ! Err: {err}')


def generate_gallery(c: Config):
    """
    Creating galleries is one of the major features of img-DB.

    Examples of filters:
    - date >= 2020 ; date <= 2021   -- to filter specific years
    - format = PNG ; bytes > 100000 -- to filter by format and disk-size
    - width > 5000 ; height > 4000  -- to filter by image width & height
    - make-model ~~ Sony            -- to filter by maker & model (case insensitive)
    - date ~ 2[0-9]{3}-12-25        -- to filter any year with December 25 (Christmas)
    """
    env = Environment(loader=FileSystemLoader(['tmpl', 'imgdb/tmpl']))
    t = env.get_template(c.tmpl)
    t.globals.update({'slugify': slugify})

    db = db_open(c.dbname)
    metas, imgs = db_filter(db, c=c)

    max_pages = len(metas) // c.wrap_at
    log.info(f'Generating {max_pages+1} galleries from {len(metas):,} pictures...')

    # add or remove attrs before publishing gallery
    for img in imgs:
        for a in c.del_attrs:
            if a in img.attrs:
                del img.attrs[a]
        for a in c.add_attrs:
            k, v = a.split('=')
            img.attrs[k] = v

    i = 1
    name, ext = splitext(c.gallery)
    if not ext:
        ext = '.htm'
    page_name = lambda n: f'{name}-{n:02}{ext}'
    while i <= max_pages + 1:
        next_page = ''
        if i <= max_pages:
            next_page = page_name(i + 1)
        with open(page_name(i), 'w') as fd:
            log.debug(f'Writing {page_name(i)}')
            fd.write(
                t.render(
                    imgs=imgs[(i - 1) * c.wrap_at : i * c.wrap_at],
                    metas=metas[(i - 1) * c.wrap_at : i * c.wrap_at],
                    next_page=next_page,
                    page_nr=i,
                    title='img-DB gallery',
                )
            )
        i += 1


def generate_links(c: Config):
    """
    Creating folders with links is one of the major features of img-DB.

    This makes it possible to natively look at your photos in a different way,
    without making copies, eg:
    - view all the pictures from a specific month-year
    - all pictures from Christmas, whatever the year
    - all pictures from specific days, maybe an event
    - all pictures taken with a specific device, like the iPhone 8
    - all pictures larger than 4k, etc etc

    After you create the folders with links, you can explore them like usual, eg:
    from Windows File Explorer, macOS Finder, Thunar, etc.

    This requires a storage file-system that supports soft or hard links, eg:
    EXT4 (linux), NFTS (windows), APFS/ HFS+ (macOS), etc.
    File-systems that DON'T support links are: FAT16, FAT32, exFAT.
    (UDF is supposed to support only hard-links)

    Examples of folders:
    - imgdb/{Date:%Y-%m-%d}/{Pth.name}  - create year-month-day folders, keeping the original file name
                                        - you should probably also add --filter 'date > 1990'
    - imgdb/{make-model}/{Pth.name}     - create camera maker+model folders, keeping the original file name
                                        - you should probably also add --filter 'make-model != -'
    - imgdb/{Date:%Y-%m}/{Date:%Y-%m-%d-%X}-{id:.6s}{Pth.suffix}
                                        - create year-month folders, using the date in the file name
    """
    tmpl = c.links
    db = db_open(c.dbname)
    metas, _ = db_filter(db, c=c)

    log.info(f'Generating {"sym" if c.sym_links else "hard"}-links "{tmpl}" for {len(metas)} pictures...')
    link = os.symlink if c.sym_links else os.link

    for meta in tqdm(metas, unit='link'):
        link_dest = Path(tmpl.format(**meta))
        link_dir = link_dest.parent
        link_exists = link_dest.is_file() or link_dest.is_symlink()
        if not c.force and link_exists:
            log.debug(f'skipping link of {meta["Pth"].name} because {link_dir.name}/{link_dest.name} exists')
            continue
        if c.force and link_exists:
            os.unlink(link_dest)

        if not link_dir.is_dir():
            link_dest.parent.mkdir(parents=True)
        try:
            log.debug(f'link: {meta["Pth"].name}  ->  {link_dir.name}/{link_dest.name}')
            link(meta['pth'], link_dest)
        except Exception as err:
            log.error(f'Link error: {err}')
