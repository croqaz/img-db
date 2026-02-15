from pathlib import Path

from fastapi.testclient import TestClient

from imgdb.server import run
from imgdb.server.run import app

run.RECENT_DBS_FILE = Path('test/fixtures/recent.htm')

client = TestClient(app)


def test_health_check():
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'


def test_find_files_basic():
    response = client.get(
        '/api/files',
        params={
            'path': ['test'],
            'exts': 'py',
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert 'count' in data
    assert 'files' in data
    assert data['count'] > 0
    files = data['files']
    assert 'test/test_img.py' in files
    assert 'test/test_server.py' in files


def test_find_files_deep():
    # Test deep search
    response = client.get('/api/files', params={'path': ['test'], 'exts': 'png', 'deep': True, 'limit': 3})

    assert response.status_code == 200
    data = response.json()
    assert len(data['files']) <= 3
    # Should find something
    assert data['count'] > 0


def test_serve_image():
    img_path = 'test/pics/Claudius_Ptolemy_The_World.png'
    response = client.get('/img', params={'path': img_path})

    assert response.status_code == 200
    assert response.headers['content-type'] == 'image/png'
    assert response.content == Path(img_path).read_bytes()


def test_gallery_settings(temp_dir):
    db_path = f'{temp_dir}/settings.htm'
    if run.RECENT_DBS_FILE.is_file():
        run.RECENT_DBS_FILE.unlink()

    response = client.post('/gallery', data={'db': db_path}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers['location'] == f'/gallery?db={db_path}'

    # Update settings via POST
    response = client.post(
        '/gallery_settings',
        params={'db': db_path, 'thumb_sz': '128'},
        data={'thumb_type': 'WEBP', 'new_setting': 'test_value'},
    )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['updated'] == 3

    db = run.ImgDB(db_path)
    assert db.meta['thumb_sz'] == '128'
    assert db.meta['thumb_type'] == 'WEBP'
    assert db.meta['new_setting'] == 'test_value'

    # Test DB file not found
    response = client.post('/gallery_settings', params={'db': 'missing.htm'})
    assert response.status_code == 404

    if run.RECENT_DBS_FILE.is_file():
        run.RECENT_DBS_FILE.unlink()


def test_gallery_settings_full(temp_dir):
    db_path = f'{temp_dir}/settings_full.htm'
    if run.RECENT_DBS_FILE.is_file():
        run.RECENT_DBS_FILE.unlink()

    client.post('/gallery', data={'db': db_path}, follow_redirects=False)

    # Define all the settings we want to update
    settings_data = {
        'operation': 'copy',
        'metadata': 'lens,iso,shutter-speed',
        'algorithms': 'contrast,top-colors',
        'v_hashes': 'ahash,dhash',
        'thumb_sz': '256',
        'thumb_qual': '85',
        'thumb_type': 'avif',
    }
    response = client.post(
        '/gallery_settings',
        params={'db': db_path},
        data=settings_data,
    )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['updated'] == 7

    # Verify persistence inside the DB file
    db = run.ImgDB(db_path)
    for k, v in settings_data.items():
        assert db.meta[k] == v

    # Test updating a subset
    subset_data = {
        'archive': '/tmp/my-archive',
        'operation': 'move',
        'thumb_qual': '90',
    }
    response = client.post(
        '/gallery_settings',
        params={'db': db_path},
        data=subset_data,
    )
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'ok'
    assert data['updated'] == 3

    db = run.ImgDB(db_path)
    assert db.meta['operation'] == 'move'
    assert db.meta['thumb_sz'] == '256'
    assert db.meta['thumb_qual'] == '90'
    assert db.meta['thumb_type'] == 'avif'


def test_create_and_explore_gallery(temp_dir):
    db_path = Path(f'{temp_dir}/new_gallery.htm')
    if run.RECENT_DBS_FILE.is_file():
        run.RECENT_DBS_FILE.unlink()

    try:
        # Create a new empty DB/gallery
        response = client.post('/gallery', data={'db': str(db_path)}, follow_redirects=False)
        assert response.status_code == 303
        assert response.headers['location'] == f'/gallery?db={db_path}'

        # Verify DB file was created
        assert db_path.is_file()

        # Explore the gallery
        response = client.get(f'/gallery?db={db_path}')
        assert response.status_code == 200
        assert 'img-DB Gallery' in response.text
        assert response.text.count('img data') == 0

        # Import the images from test/pics/
        response = client.post(
            '/import',
            params={'db': str(db_path)},
            data={'input': 'test/pics'},
        )
        assert response.status_code == 200
        data = response.json()
        assert data['available'] == 3
        assert data['imported'] == 3

        # Explore the gallery again to update RECENT_DBS_FILE
        response = client.get(f'/gallery?db={db_path}')
        assert response.status_code == 200
        assert 'img-DB Gallery' in response.text
        assert response.text.count('img data') == 3

        # Check that RECENT_DBS_FILE contains link
        assert run.RECENT_DBS_FILE.is_file()
        recent_content = run.RECENT_DBS_FILE.read_text()
        assert str(db_path) in recent_content
        # Check that the recent DBs contains the 3 images from test/pics/
        assert 'data-pth="test/pics/Aldrin_Apollo_11.jpg"' in recent_content
        assert 'data-pth="test/pics/Claudius_Ptolemy_The_World.png"' in recent_content
        assert 'data-pth="test/pics/Mona_Lisa_by_Leonardo_da_Vinci.jpg"' in recent_content

        # Open home/index
        response = client.get('/')
        assert response.status_code == 200

        # Check home/index contains recently explored gallery
        assert str(db_path) in response.text
        assert 'new_gallery.htm' in response.text

    finally:
        if run.RECENT_DBS_FILE.is_file():
            run.RECENT_DBS_FILE.unlink()


def test_gallery_negative_cases():
    # No DB specified
    response = client.get('/gallery')
    assert response.status_code == 200
    assert 'Please provide a DB file path to load!' in response.text

    # DB file not found
    response = client.get('/gallery', params={'db': 'missing.htm'})
    assert response.status_code == 200
    assert 'DB file not found: missing.htm!' in response.text

    # DB load some random non-HTML file
    bad_db = 'test/pics/Aldrin_Apollo_11.jpg'
    response = client.get('/gallery', params={'db': bad_db})
    assert response.status_code == 200


def test_import_negative_cases(temp_dir):
    # Missing DB file
    response = client.post(
        '/import',
        params={'db': 'missing.htm'},
        data={'input': 'test/pics'},
    )
    assert response.status_code == 404

    # Missing input
    db_path = f'{temp_dir}/import_negative.htm'
    if run.RECENT_DBS_FILE.is_file():
        run.RECENT_DBS_FILE.unlink()
    try:
        client.post('/gallery', data={'db': db_path}, follow_redirects=False)
        response = client.post('/import', params={'db': db_path})
        assert response.status_code == 400
    finally:
        if run.RECENT_DBS_FILE.is_file():
            run.RECENT_DBS_FILE.unlink()
