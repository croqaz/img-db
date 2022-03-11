"""
Creating folders with links is one of the major features of img-DB.

This makes it possible to natively look at your photos in a different way,
without making copies, eg:
- view all the pictures from a specific month-year
- all pictures from Christmas whatever the year
- all pictures from specific days, maybe an event
- all pictures taken with a specific device like the iPhone 8
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
# import os


def generate_links(db, opts: Namespace):
    imgs = db_filter(db, opts)
    print(f'Generating links for {len(imgs)} pictures...')
    for el in imgs:
        src = Path(el.attrs['data-pth'])
        dt = el.attrs.get('data-date', '')
        mm = el.attrs.get('data-make-model', '')
        print(src, dt, mm)
