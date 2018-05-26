"""
pytest local configuration plug-in
"""

import os.path
import subprocess
import sys
from shutil import rmtree

import pytest


@pytest.fixture(scope='session')
def wheels_and_eggs():
    """Build wheels and eggs from test distributions."""
    test_distributions = "complex-dist", "simple.dist", "headers.dist", "unicode.dist"
    files = []
    pwd = os.path.abspath(os.curdir)
    this_dir = os.path.dirname(__file__)
    for dist in test_distributions:
        os.chdir(os.path.join(this_dir, 'testdata', dist))
        subprocess.check_call([sys.executable, 'setup.py', 'bdist_egg', 'bdist_wheel'])
        dist_path = os.path.join(os.curdir, 'dist')
        files.extend([os.path.abspath(os.path.join(dist_path, fname))
                      for fname in os.listdir(dist_path)
                      if os.path.splitext(fname)[1] in ('.whl', '.egg')])

    os.chdir(pwd)
    yield files

    for dist in test_distributions:
        for subdir in ('build', 'dist'):
            try:
                rmtree(os.path.join(this_dir, dist, subdir))
            except OSError:
                pass


@pytest.fixture(scope='session')
def wheel_paths(wheels_and_eggs):
    return sorted(fname for fname in wheels_and_eggs if fname.endswith('.whl'))


@pytest.fixture(scope='session')
def egg_paths(wheels_and_eggs):
    return sorted(fname for fname in wheels_and_eggs if fname.endswith('.egg'))
