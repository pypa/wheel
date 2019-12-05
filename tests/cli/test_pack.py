import os
from zipfile import ZipFile

from wheel.cli.pack import pack

THISDIR = os.path.dirname(__file__)
TESTWHEEL_NAME = 'test-1.0-py2.py3-none-any.whl'
TESTWHEEL_PATH = os.path.join(THISDIR, '..', 'testdata', TESTWHEEL_NAME)


def test_pack_no_build_number(tmpdir_factory, tmpdir):
    unpack_dir = str(tmpdir_factory.mktemp('wheeldir'))
    build_number = None
    filename = 'test-1.0-py2.py3-none-any.whl'
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


def test_pack_build_number(tmpdir_factory, tmpdir):
    unpack_dir = str(tmpdir_factory.mktemp('wheeldir'))
    build_number = '2b'
    filename = 'test-1.0-2b-py2.py3-none-any.whl'
    with ZipFile(TESTWHEEL_PATH) as zf:
        old_record = zf.read('test-1.0.dist-info/RECORD')
        old_record_lines = sorted(line.rstrip() for line in old_record.split(b'\n')
                                  if line and line.find(b"WHEEL") == -1)
        zf.extractall(unpack_dir)

    pack(unpack_dir, str(tmpdir), build_number)
    new_wheel_path = tmpdir.join(filename)
    assert new_wheel_path.isfile()

    with ZipFile(str(new_wheel_path)) as zf:
        new_record = zf.read('test-1.0.dist-info/RECORD')
        new_record_lines = sorted(line.rstrip() for line in new_record.split(b'\n')
                                  if line and line.find(b"WHEEL") == -1)

    assert new_record_lines == old_record_lines


def test_pack_appends_build_to_wheel_file(tmpdir_factory, tmpdir):
    unpack_dir = str(tmpdir_factory.mktemp('wheeldir'))
    build_number = '2b'
    filename = 'test-1.0-2b-py2.py3-none-any.whl'
    with ZipFile(TESTWHEEL_PATH) as zf:
        zf.extractall(unpack_dir)

    pack(unpack_dir, str(tmpdir), build_number)
    new_wheel_path = tmpdir.join(filename)
    assert new_wheel_path.isfile()

    with ZipFile(str(new_wheel_path)) as zf:
        new_record = zf.read('test-1.0.dist-info/WHEEL')
        new_record_lines = sorted(line.rstrip() for line in new_record.split(b'\n')
                                  if line and line.startswith(b"Build:"))

    assert len(new_record_lines) == 1
    assert new_record_lines[0] == b'Build: 2b'


def test_pack_multiple_times_one_build_record(tmpdir_factory, tmpdir):
    unpack_dir = str(tmpdir_factory.mktemp('wheeldir'))
    second_unpack_dir = str(tmpdir_factory.mktemp('wheeldir_second'))
    first_build_number = '1'
    first_wheel_name = 'test-1.0-1-py2.py3-none-any.whl'
    final_build_number = '2'
    final_wheel_name = 'test-1.0-2-py2.py3-none-any.whl'

    # GIVEN
    with ZipFile(TESTWHEEL_PATH) as zf:
        zf.extractall(unpack_dir)

    pack(unpack_dir, str(tmpdir), first_build_number)
    first_wheel_path = tmpdir.join(first_wheel_name)
    assert first_wheel_path.isfile()

    # WHEN
    with ZipFile(str(first_wheel_path)) as zf:
        zf.extractall(second_unpack_dir)
    pack(second_unpack_dir, str(tmpdir), final_build_number)
    final_wheel_path = tmpdir.join(final_wheel_name)
    assert final_wheel_path.isfile()

    # THEN
    with ZipFile(str(final_wheel_path)) as zf:
        final_record = zf.read('test-1.0.dist-info/WHEEL')
        final_record_lines = sorted(line.rstrip() for line in final_record.split(b'\n')
                                    if line and line.startswith(b"Build:"))

    assert len(final_record_lines) == 1
    assert final_record_lines[0] == b'Build: 2'
