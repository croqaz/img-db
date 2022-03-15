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
from .db import db_filter

from argparse import Namespace
from pathlib import Path
import os


def generate_links(db, opts: Namespace):
    """
    Examples of folders:
    - imgdb/{date:%Y-%m-%d}/{pth.name}  - create year-month-day folders, keeping the original file name
    - imgdb/{make-model}/{pth.name}     - create camera maker+model folders, keeping the original file name
    - imgdb/{date:%Y-%m}/{date:%Y-%m-%d-%X}-{id:.6s}{pth.suffix} - create year-month folders, using the date in the file name
    """
    tmpl = opts.links
    metas, _ = db_filter(db, opts)
    if opts.sym_links:
        link = os.symlink
    else:
        link = os.link
    print(f'Generating {"sym" if opts.sym_links else "hard"}-links "{tmpl}" for {len(metas)} pictures...')
    for meta in metas:
        link_dest = Path(tmpl.format(**meta))
        if link_dest.is_file():
            continue
        print('-> ', link_dest)
        if not link_dest.parent.is_dir():
            link_dest.parent.mkdir(parents=True)
        link(meta['pth'], link_dest)
