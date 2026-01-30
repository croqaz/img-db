from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query

from ..config import Config
from ..fsys import find_files

app = FastAPI()


@app.get('/api/files')
def list_files_api(
    path: list[str] = Query(..., title='path', description='The path to search for files'),  # NOQA
    exts: str = '',
    limit: int = 0,
    deep: bool = False,
    shuffle: bool = False,
):
    c = Config(
        exts=exts,
        limit=limit,
        deep=deep,
        shuffle=shuffle,
    )
    input_paths = [Path(p) for p in path]
    found_files = find_files(input_paths, c)
    return {
        'count': len(found_files),
        'files': [str(p) for p in found_files],
    }
