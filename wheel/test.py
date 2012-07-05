import os

from nose.tools import assert_true, assert_false, assert_equal, raises
from .install import WheelFile

def test_findable():
    """Make sure pkg_resources can find us."""
    import pkg_resources
    assert pkg_resources.working_set.by_key['wheel'].version

def test_egg_re():
    """Make sure egg_info_re matches."""
    from . import egg2wheel
    import pkg_resources
    egg_names = open(pkg_resources.resource_filename('wheel', 'eggnames.txt'))
    for line in egg_names:
        line = line.strip()
        if not line: continue
        assert egg2wheel.egg_info_re.match(line), line
