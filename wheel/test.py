import os

from .install import WheelFile

def test_findable():
    """Make sure pkg_resources can find us."""
    import pkg_resources
    assert pkg_resources.working_set.by_key['wheel'].version

def test_wheel():
    for filename in os.listdir(os.getenv('WHEELBASE')):
        print filename