from fastapi.testclient import TestClient

from imgdb.server.run import app

client = TestClient(app)

def test_find_files_basic():
    response = client.get("/api/files", params={
        "path": ["test"],
        "exts": "py",
    })

    assert response.status_code == 200
    data = response.json()
    assert "count" in data
    assert "files" in data
    assert data["count"] > 0
    files = data["files"]
    assert "test/test_img.py" in files
    assert "test/test_server.py" in files

def test_find_files_deep():
    # Test deep search
    response = client.get("/api/files", params={
        "path": ["test"],
        "exts": "png",
        "deep": True,
        "limit": 3
    })

    assert response.status_code == 200
    data = response.json()
    assert len(data["files"]) <= 3
    # Should find something
    assert data["count"] > 0
