"""
pytest local configuration plug-in
"""

import os.path
import subprocess
import sys

import pytest


@pytest.fixture(scope='session')
def wheels_and_eggs(tmpdir_factory):
    """Build wheels and eggs from test distributions."""
    test_distributions = "complex-dist", "simple.dist", "headers.dist"
    if sys.version_info >= (3, 6):
        # Only Python 3.6+ can handle packaging unicode file names reliably
        # across different platforms
        test_distributions += ("unicode.dist",)

    if sys.platform != 'win32':
        # ABI3 extensions don't really work on Windows
        test_distributions += ("abi3extension.dist",)

    pwd = os.path.abspath(os.curdir)
    this_dir = os.path.dirname(__file__)
    build_dir = tmpdir_factory.mktemp('build')
    dist_dir = tmpdir_factory.mktemp('dist')
    for dist in test_distributions:
        os.chdir(os.path.join(this_dir, 'testdata', dist))
        subprocess.check_call([sys.executable, 'setup.py',
                               'bdist_egg', '-b', str(build_dir), '-d', str(dist_dir),
                               'bdist_wheel', '-b', str(build_dir), '-d', str(dist_dir)])

    os.chdir(pwd)
    return sorted(str(fname) for fname in dist_dir.listdir() if fname.ext in ('.whl', '.egg'))


@pytest.fixture(scope='session')
def wheel_paths(wheels_and_eggs):
    return [fname for fname in wheels_and_eggs if fname.endswith('.whl')]


@pytest.fixture(scope='session')
def egg_paths(wheels_and_eggs):
    return [fname for fname in wheels_and_eggs if fname.endswith('.egg')]
