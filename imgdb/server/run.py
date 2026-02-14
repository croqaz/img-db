from __future__ import annotations

import io
import mimetypes
from pathlib import Path
from typing import Any

import rawpy
from bs4 import BeautifulSoup, Tag
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from jinja2 import Environment, FileSystemLoader
from PIL import Image

from ..config import Config
from ..db import ImgDB
from ..fsys import find_files
from ..img import RAW_EXTS

RECENT_DBS_FILE = Path.home() / '.imgdb' / 'recent.htm'

app = FastAPI()
app.mount('/static', StaticFiles(directory=Path(__file__).parent / 'static'), name='static')
templates = Environment(loader=FileSystemLoader(Path(__file__).parent / 'views'))


@app.get('/api/health')
def health_check():
    """A simple health-check endpoint."""
    return {'status': 'ok'}


def update_recent_dbs(db_path: str, images: list, disk_size_bytes: int):
    """
    Adds or refreshes a DB entry in the recent.htm file.
    This is a HTML5 file that can be viewed in a browser, but also with the
    metadata and info required to restore old DB files.
    """
    RECENT_DBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if RECENT_DBS_FILE.is_file():
        soup = BeautifulSoup(RECENT_DBS_FILE.read_text(), 'lxml')
        body = soup.find('body')
    else:
        soup = None
        body = None

    if not body:
        soup = BeautifulSoup(
            '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            '<title>Recent img-DB Databases</title><style>'
            'body { font-family: sans-serif; } '
            'article { border: 1px solid #ccc; padding: 1em; margin-bottom: 1em; } '
            '.gallery-preview img { max-width: 150px; max-height: 150px; margin: 5px; }'
            '</style></head><body><h1>Recent Databases</h1></body></html>',
            'lxml',
        )
        body = soup.body

    # Remove existing entry for this DB path
    existing = body.find('article', attrs={'data-db-path': db_path})
    if existing:
        existing.decompose()

    # Create new entry
    article = soup.new_tag(
        'article',
        attrs={
            'class': 'recent-db-entry',
            'data-db-path': db_path,
            'data-image-count': str(len(images)),
            'data-total-size': str(disk_size_bytes),
        },
    )

    h2 = soup.new_tag('h2')
    a = soup.new_tag('a', href=f'/gallery?db={db_path}')
    a.string = Path(db_path).name
    h2.append(a)
    article.append(h2)

    p_stats = soup.new_tag('p')
    disk_size_mb = f'{disk_size_bytes / (1024 * 1024):.2f} MB'
    p_stats.string = f'Contains {len(images)} images ({disk_size_mb})'
    article.append(p_stats)

    # Add X most recent images
    if images:
        preview_div = soup.new_tag('div', attrs={'class': 'gallery-preview'})
        # Assuming images are sorted by date, newest first
        for img in images[:5]:
            img_path = img.attrs.get('data-pth', '')
            img_src = img.attrs.get('src', '')
            if img_path and img_src:
                img_tag = soup.new_tag('img', src=img_src, attrs={'data-pth': img_path})
                preview_div.append(img_tag)
        article.append(preview_div)

    # Insert after the H1, or at the beginning of the body
    h1 = body.find('h1')
    if h1:
        h1.insert_after(article)
    else:
        body.insert(0, article)

    # Limit to X most recent DBs
    all_dbs = body.find_all('article', {'class': 'recent-db-entry'})
    if len(all_dbs) > 5:
        for old_entry in all_dbs[5:]:
            old_entry.decompose()
    # Remove all entries with missing files
    for article in all_dbs:
        db_file = Path(article.attrs['data-db-path'])
        if not db_file.is_file():
            article.decompose()

    RECENT_DBS_FILE.write_text(str(soup))


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    """The home page of the app."""
    recent_dbs = []
    if RECENT_DBS_FILE.is_file():
        soup = BeautifulSoup(RECENT_DBS_FILE.read_text(), 'lxml')
        for article in soup.find_all('article', {'class': 'recent-db-entry'}):
            if isinstance(article, Tag):
                recent_dbs.append(article)
    return templates.get_template('index.html').render(
        title='img-DB',
        recent_dbs=recent_dbs,
    )


@app.post('/gallery', response_class=HTMLResponse)
def create_gallery(
    db: str = Form(..., title='db', description='Path to the new img-db HTML'),
):
    """Create a new empty DB/gallery."""
    ImgDB(fname=db, elems=[]).save()
    # Should we also add it to recent galleries?
    # It won't have any images, but it will be visible there and easier to open after creating.
    update_recent_dbs(db, [], 0)
    return RedirectResponse(url=f'/gallery?db={db}', status_code=303)


@app.get('/gallery', response_class=HTMLResponse)
def gallery(
    request: Request,
    db: str | None = Query(default=None, title='db', description='Path to img-db HTML file'),
    q: str = Query('', title='filter', description='Filter images by path'),
):
    """The DB/gallery page explorer."""
    error = ''
    images = []
    db_meta = {}
    disk_size = '0 MB'
    db_path = Path(db or '')
    if not db:
        error = 'Please provide a DB file path to load!'
    else:
        if db_path.is_file():
            db_obj = ImgDB(db)
            images = list(db_obj.images)
            db_meta = db_obj.meta
        else:
            error = f'DB file not found: {db}!'

    # Filter by image path (unused for now)
    if q and images:  # pragma: no cover
        q = q.lower()
        images = [img for img in images if q in img.attrs.get('data-pth', '').lower()]

    if not error:
        disk_size_bytes = sum(int(img.attrs.get('data-bytes', 0)) for img in images)
        disk_size = f'{disk_size_bytes / (1024 * 1024):.2f} MB'
        update_recent_dbs(db, images, disk_size_bytes)

    return templates.get_template('gallery.html').render(
        title='img-DB Gallery',
        db_path=db_path,
        db_meta=db_meta,
        images=images,
        disk_size=disk_size,
        error=error,
    )


@app.post('/gallery_settings')
async def gallery_settings(
    request: Request,
    db: str = Query(..., title='db', description='Path to the gallery that needs to be updated'),
):
    """Update DB/gallery metadata/settings."""
    if not Path(db).is_file():
        return HTMLResponse(content=f'DB file not found: {db}', status_code=404)

    db_obj = ImgDB(db)
    # update DB meta with provided key-values
    # support both query params (e.g. ?db=...&thumb_sz=128) and form data
    params: dict[str, Any] = dict(request.query_params)
    form_data = await request.form()
    # combine query params and form data, form data overrides query params
    for k, v in form_data.items():
        params[k] = v

    updated = 0
    for k, v in params.items():
        if k == 'db':
            continue
        db_obj.meta[k] = v
        updated += 1

    if updated > 0:
        db_obj.save()
        return {'status': 'ok', 'updated': updated}
    return {'status': 'no changes'}


@app.get('/img')
def serve_image(
    path: str = Query(..., title='path', description='The path of the image'),
):
    """Serve one image file from disk, converting RAW files to JPEG on-the-fly."""
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
