from tempfile import TemporaryDirectory

import pytest
from attrs import define


@define(slots=False)
class Args:
    inputs: list = []
    output: str = ''
    dbname: str = ''
    operation: str = 'copy'
    c_hashes: str = 'blake2b'
    v_hashes: str = 'dhash'
    metadata: str = ''
    algorithms: str = ''
    limit: int = 0
    deep: bool = False
    force: bool = False
    skip_imported: bool = False
    shuffle: bool = False
    verbose: bool = False


@pytest.fixture(scope='function')
def temp_dir():
    with TemporaryDirectory(prefix='imgdb-') as tmpdir:
        yield tmpdir
