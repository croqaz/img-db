from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

from ..config import Config
from ..db import ImgDB
from ..fsys import find_files

app = FastAPI()
templates = Environment(loader=FileSystemLoader(Path(__file__).parent / 'views'))


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    """The home page of the app"""
    return templates.get_template('index.html').render(
        request=request,
        title='img-DB',
    )


@app.get('/gallery', response_class=HTMLResponse)
def gallery(
    request: Request,
    db: str | None = Query(default=None, title='db', description='Path to img-db HTML file'),
    q: str = Query('', title='filter', description='Filter images by path'),
):
    """The gallery page of the app."""
    error = ''
    images = []
    db_path = db.strip() if db else ''
    if not db_path:
        error = 'Please provide a database file path to load.'
    else:
        db_file = Path(db_path)
        if not db_file.is_file():
            error = f'DB file not found: {db_path}'
        else:
            try:
                db_obj = ImgDB(fname=db_path)
                images = list(db_obj.images)
            except Exception as err:
                error = f'Failed to open DB: {err}'

    # Filter by path query
    if q and images:
        q = q.lower()
        images = [img for img in images if q in img.attrs.get('data-pth', '').lower()]

    return templates.get_template('gallery.html').render(
        request=request,
        title='img-DB Gallery',
        db_path=db_path,
        images=images,
        error=error,
        q=q,
    )


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
