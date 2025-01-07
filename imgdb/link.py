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
"""

import os
from pathlib import Path

from bs4 import BeautifulSoup
from tqdm import tqdm

from .config import g_config
from .db import db_filter
from .log import log


def generate_links(db: BeautifulSoup, c=g_config):
    """
    Examples of folders:
    - imgdb/{Date:%Y-%m-%d}/{Pth.name}  - create year-month-day folders, keeping the original file name
                                        - you should probably also add --filter 'date > 1990'
    - imgdb/{make-model}/{Pth.name}     - create camera maker+model folders, keeping the original file name
                                        - you should probably also add --filter 'make-model != -'
    - imgdb/{Date:%Y-%m}/{Date:%Y-%m-%d-%X}-{id:.6s}{Pth.suffix}
                                        - create year-month folders, using the date in the file name
    """
    tmpl = c.links
    metas, _ = db_filter(db, c=c)

    log.info(f'Generating {"sym" if c.sym_links else "hard"}-links "{tmpl}" for {len(metas)} pictures...')
    link = os.symlink if c.sym_links else os.link

    for meta in tqdm(metas, unit='link'):
        link_dest = Path(tmpl.format(**meta))
        link_dir = link_dest.parent
        if not c.force and link_dest.is_file() or link_dest.is_symlink():
            log.debug(f'skipping link of {meta["Pth"].name} because {link_dir.name}/{link_dest.name} exists')
            continue

        log.debug(f'link: {meta["Pth"].name}  ->  {link_dir.name}/{link_dest.name}')
        if not link_dir.is_dir():
            link_dest.parent.mkdir(parents=True)
        try:
            os.unlink(link_dest)
            link(meta['pth'], link_dest)
        except Exception as err:
            log.error(f'Link error: {err}')
