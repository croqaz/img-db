from pathlib import Path
from random import shuffle

from .config import Config
from .log import log


def find_files(folders: list[Path], c: Config) -> list[Path]:
    found = 0
    stop = False
    to_proc = []

    for pth in folders:
        if stop:
            break
        if isinstance(pth, str):
            pth = Path(pth)
        try:
            if not pth.is_dir():
                raise ValueError(f'Path "{pth}" is not a folder!')
        except PermissionError:
            log.error(f'Permission denied accessing: {pth}')
            continue
        except Exception as err:
            log.error(f'Error processing directory {pth}: {err}')
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
            # Check for duplicates only in case of multiple inputs (potentially slow)
            if len(folders) == 1 or p not in to_proc:
                to_proc.append(p)
            if c.limit and c.limit > 0 and len(to_proc) >= c.limit:
                stop = True
                break

    log.info(f'Found: {found:,} files, to process: {len(to_proc):,} files')
    return to_proc
