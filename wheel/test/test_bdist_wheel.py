import json
import os.path
from zipfile import ZipFile

import jsonschema
import pytest

THISDIR = os.path.dirname(__file__)


def test_no_scripts(wheel_paths):
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if 'complex-dist' in path)
    for entry in ZipFile(path).infolist():
        assert '.data/scripts/' not in entry.filename


def test_pydist(wheel_paths):
    """Make sure metadata.json exists and validates against our schema."""
    # XXX this test may need manual cleanup of older wheels
    with open(os.path.join(THISDIR, 'pydist-schema.json')) as f:
        pymeta_schema = json.load(f)

    for wheel_path in wheel_paths:
        with ZipFile(wheel_path) as whl:
            for entry in ZipFile(wheel_path).infolist():
                if entry.filename.endswith('/metadata.json'):
                    pymeta = json.loads(whl.read(entry).decode('utf-8'))
                    jsonschema.validate(pymeta, pymeta_schema)
                    break
            else:
                pytest.fail('No metadata.json found in %s' % wheel_path)
