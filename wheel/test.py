import os

from nose.tools import assert_true, assert_false, assert_equal, raises
from .install import WheelFile

def test_findable():
    """Make sure pkg_resources can find us."""
    import pkg_resources
    assert pkg_resources.working_set.by_key['wheel'].version
    