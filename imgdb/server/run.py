from __future__ import annotations

import io
import mimetypes
from pathlib import Path

import rawpy
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from PIL import Image

from ..config import Config
from ..db import ImgDB
from ..fsys import find_files
from ..img import RAW_EXTS

app = FastAPI()
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')
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


@app.get('/img')
def serve_image(
    path: str = Query(..., title='path', description='The path of the image'),
):
    """Serve an image file given its path."""
    img_path = Path(path)
    headers = {'Cache-Control': 'public, max-age=31536000, immutable'}
    if not img_path.is_file():
        return HTMLResponse(content='Image not found', status_code=404)
    if img_path.suffix.lower() in RAW_EXTS:
        with rawpy.imread(path) as raw:
            rgb_array = raw.postprocess(use_auto_wb=True, no_auto_bright=True, output_bps=8)
            raw_img = Image.fromarray(rgb_array, mode='RGB')
            img_io = io.BytesIO()
            raw_img.save(img_io, 'jpeg', progressive=True, quality=80)
            img_io.seek(0)
            return HTMLResponse(content=img_io.read(), headers=headers, media_type='image/jpeg')

    # Guess media type from extension
    mime, _ = mimetypes.guess_file_type(img_path)
    return HTMLResponse(
        content=img_path.read_bytes(),
        headers=headers,
        media_type=mime or 'application/octet-stream',
    )


@app.get('/api/health')
def health_check():
    """A simple health-check endpoint."""
    return {'status': 'ok'}


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
