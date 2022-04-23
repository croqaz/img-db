from tempfile import TemporaryDirectory
import pytest


@pytest.fixture(scope='function')
def temp_dir():
    with TemporaryDirectory(prefix='imgdb-') as tmpdir:
        yield tmpdir
