from __future__ import annotations

import io
import mimetypes
from pathlib import Path

import rawpy
from bs4 import BeautifulSoup, Tag
from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
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

    disk_size_bytes = sum(int(img.attrs.get('data-bytes', 0)) for img in images)
    disk_size = f'{disk_size_bytes / (1024 * 1024):.2f} MB'

    if images and not error:
        update_recent_dbs(db_path, images, disk_size_bytes)

    return templates.get_template('gallery.html').render(
        title='img-DB Gallery',
        db_path=db_path,
        images=images,
        disk_size=disk_size,
        error=error,
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
