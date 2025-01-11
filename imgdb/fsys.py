import sys
from pathlib import Path
from random import shuffle
from typing import List

from .config import Config, g_config
from .log import log


def find_files(folders: List[Path], c: Config) -> List[Path]:
    found = 0
    stop = False
    to_proc = []

    for pth in folders:
        if stop:
            break
        if isinstance(pth, str):
            pth = Path(pth)
        if not pth.is_dir():
            log.warn(f'Path "{pth}" is not a folder!')
            continue
        glob_pattern = '**/*.*' if c.deep else '*.*'
        if c.shuffle:
            imgs = list(pth.glob(glob_pattern))
            shuffle(imgs)
        else:
            imgs = sorted(pth.glob(glob_pattern))
        found += len(imgs)
        for p in imgs:
            if c.exts and p.suffix.lower() not in c.exts:
                continue
            to_proc.append(p)
            if c.limit and c.limit > 0 and len(to_proc) >= c.limit:
                stop = True
                break

    log.info(f'Found: {found:,} files, to process: {len(to_proc):,} files')
    return to_proc


if __name__ == '__main__':
    # g_config.deep = True
    # g_config.shuffle = True
    pth = Path(sys.argv[1])
    print(find_files([pth], g_config))
