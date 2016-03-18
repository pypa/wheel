"""
pytest local configuration plug-in
"""

import gc
import warnings

import pytest

@pytest.yield_fixture(scope='function', autouse=True)
def fail_on_ResourceWarning():
    """This fixture captures ResourceWarning's and raises an assertion error
    describing the file handles left open.

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
        warnings.resetwarnings() # clear all filters
        warnings.simplefilter('ignore') # ignore all
        warnings.simplefilter('always', ResourceWarning) # add filter
        yield # run tests in this context
        gc.collect() # run garbage collection (for pypy3)
        # display the problematic filenames if any warnings were caught
        assert not caught, '\n'.join((str(warning.message) for warning in caught))
