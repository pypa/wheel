"""
pytest local configuration plug-in
"""

import gc
import os.path
import subprocess
import sys
from shutil import rmtree

import pytest
import warnings

THISDIR = os.path.dirname(__file__)


@pytest.fixture(autouse=True)
def error_on_ResourceWarning():
    """This fixture captures ResourceWarning's and reports an "error"
    describing the file handles left open.

    This is shown regardless of how successful the test was, if a test fails
    and leaves files open then those files will be reported.  Ideally, even
    those files should be closed properly after a test failure or exception.

    Since only Python 3 and PyPy3 have ResourceWarning's, this context will
    have no effect when running tests on Python 2 or PyPy.

    Because of autouse=True, this function will be automatically enabled for
    all test_* functions in this module.

    This code is primarily based on the examples found here:
    https://stackoverflow.com/questions/24717027/convert-python-3-resourcewarnings-into-exception
    """
    try:
        ResourceWarning
    except NameError:
        # Python 2, PyPy
        yield
        return

    # Python 3, PyPy3
    with warnings.catch_warnings(record=True) as caught:
        warnings.resetwarnings()  # clear all filters
        warnings.simplefilter('ignore')  # ignore all
        warnings.simplefilter('always', ResourceWarning)  # noqa: F821
        yield  # run tests in this context
        gc.collect()  # run garbage collection (for pypy3)
        if caught:
            pytest.fail('The following file descriptors were not closed properly:\n' +
                        '\n'.join((str(warning.message) for warning in caught)),
                        pytrace=False)


@pytest.fixture(scope='session')
def wheels_and_eggs():
    """Build wheels and eggs from test distributions."""
    test_distributions = "complex-dist", "simple.dist", "headers.dist", "unicode.dist"
    files = []
    pwd = os.path.abspath(os.curdir)
    for dist in test_distributions:
        os.chdir(os.path.join(THISDIR, dist))
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
                rmtree(os.path.join(THISDIR, dist, subdir))
            except OSError:
                pass


@pytest.fixture(scope='session')
def wheel_paths(wheels_and_eggs):
    return sorted(fname for fname in wheels_and_eggs if fname.endswith('.whl'))


@pytest.fixture(scope='session')
def egg_paths(wheels_and_eggs):
    return sorted(fname for fname in wheels_and_eggs if fname.endswith('.egg'))
