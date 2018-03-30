from zipfile import ZipFile


def test_no_scripts(wheel_paths):
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if 'complex-dist' in path)
    for entry in ZipFile(path).infolist():
        assert '.data/scripts/' not in entry.filename
