import os
from zipfile import ZipFile

import pytest

from wheel.cli.pack import pack

THISDIR = os.path.dirname(__file__)
TESTWHEEL_NAME = 'test-1.0-py2.py3-none-any.whl'
TESTWHEEL_PATH = os.path.join(THISDIR, '..', 'testdata', TESTWHEEL_NAME)


@pytest.mark.parametrize('build_number, filename', [
    (None, 'test-1.0-py2.py3-none-any.whl'),
    ('2b', 'test-1.0-2b-py2.py3-none-any.whl')
], ids=['nobuildnum', 'buildnum'])
def test_pack(tmpdir_factory, tmpdir, build_number, filename):
    unpack_dir = str(tmpdir_factory.mktemp('wheeldir'))
    with ZipFile(TESTWHEEL_PATH) as zf:
        old_record = zf.read('test-1.0.dist-info/RECORD')
        old_record_lines = sorted(line.rstrip() for line in old_record.split(b'\n') if line)
        zf.extractall(unpack_dir)

    pack(unpack_dir, str(tmpdir), build_number)
    new_wheel_path = tmpdir.join(filename)
    assert new_wheel_path.isfile()

    with ZipFile(str(new_wheel_path)) as zf:
        new_record = zf.read('test-1.0.dist-info/RECORD')
        new_record_lines = sorted(line.rstrip() for line in new_record.split(b'\n') if line)

    assert new_record_lines == old_record_lines
