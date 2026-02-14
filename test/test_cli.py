from pathlib import Path

from imgdb.__main__ import main
from imgdb.db import ImgDB


def test_cli_add_delete(temp_dir):
    db_path = Path(f'{temp_dir}/test-db.htm')
    archive = Path(f'{temp_dir}/archive')

    main(['add', 'test/pics', '--db', str(db_path), '--output', str(archive), '--operation', 'copy', '--limit', '2'])
    assert db_path.is_file()
    db = ImgDB(str(db_path))
    assert len(db) == 2

    main(['del', '--db', str(db_path), '--filter', 'width > 1200'])
    db = ImgDB(str(db_path))
    assert len(db) == 1
