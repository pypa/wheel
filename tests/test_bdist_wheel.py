# coding: utf-8
from zipfile import ZipFile


def test_no_scripts(wheel_paths):
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if 'complex_dist' in path)
    for entry in ZipFile(path).infolist():
        assert '.data/scripts/' not in entry.filename


def test_unicode_record(wheel_paths):
    path = next(path for path in wheel_paths if 'unicode.dist' in path)
    with ZipFile(path) as zf:
        record = zf.read('unicode.dist-0.1.dist-info/RECORD')

    assert u'åäö_日本語.py'.encode('utf-8') in record
