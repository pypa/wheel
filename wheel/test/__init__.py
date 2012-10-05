import os
import distutils
import pkg_resources
import sys

from nose.tools import assert_true, assert_false, assert_equal, raises

import wheel.util
from wheel import egg2wheel
from wheel.install import WheelFile


def test_findable():
    """Make sure pkg_resources can find us."""
    assert pkg_resources.working_set.by_key['wheel'].version


def test_egg_re():
    """Make sure egg_info_re matches."""
    egg_names = open(pkg_resources.resource_filename('wheel', 'eggnames.txt'))
    for line in egg_names:
        line = line.strip()
        if not line:
            continue
        assert egg2wheel.egg_info_re.match(line), line


def test_compatibility_tags():
    """Test compatibilty tags are working."""
    wf = WheelFile("package-1.0.0-cp32.cp33-noabi-noarch.whl")
    assert_equal(list(wf.compatibility_tags),
                 [('cp32', 'noabi', 'noarch'), ('cp33', 'noabi', 'noarch')])
    assert_equal(wf.arity, 2)

    wf2 = WheelFile("package-1.0.0-1st-cp33-noabi-noarch.whl")
    wf2_info = wf2.parsed_filename.groupdict()
    assert wf2_info['build'] == '1st', wf2_info


def test_bdist_wheel():
    """Make sure bdist_wheel finish without errors."""
    pwd = os.curdir
    simpledist = pkg_resources.resource_filename('wheel.test', 'simple.dist')
    os.chdir(simpledist)    
    try:
        sys.argv = ['', 'bdist_wheel']
        exec(compile(open('setup.py').read(), 'setup.py', 'exec'))
    finally:
        os.chdir(pwd)


def test_util():
    """Test functions in util.py."""
    for i in range(10):
        before = b'*' * i
        encoded = wheel.util.urlsafe_b64encode(before)
        assert not encoded.endswith(b'=')
        after = wheel.util.urlsafe_b64decode(encoded)
        assert before == after


def test_pick_best():
    """Test the wheel ranking algorithm."""
    def get_tags(res):
        info = res[-1].parsed_filename.groupdict()
        return info['pyver'], info['abi'], info['plat']

    cand_tags = [('py27', 'noabi', 'noarch'), ('py26', 'noabi', 'noarch'),
                 ('cp27', 'noabi', 'linux_i686'),
                 ('cp26', 'noabi', 'linux_i686'),
                 ('cp27', 'noabi', 'linux_x86_64'),
                 ('cp26', 'noabi', 'linux_x86_64')]
    cand_wheels = [WheelFile('testpkg-1.0-%s-%s-%s.whl' % t)
                   for t in cand_tags]

    supported = [('cp27', 'noabi', 'linux_i686'), ('py27', 'noabi', 'noarch')]
    supported2 = [('cp27', 'noabi', 'linux_i686'), ('py27', 'noabi', 'noarch'),
                  ('cp26', 'noabi', 'linux_i686'), ('py26', 'noabi', 'noarch')]
    supported3 = [('cp26', 'noabi', 'linux_i686'), ('py26', 'noabi', 'noarch'),
                  ('cp27', 'noabi', 'linux_i686'), ('py27', 'noabi', 'noarch')]

    for supp in (supported, supported2, supported3):
        context = lambda: list(supp)
        for wheel in cand_wheels:
            wheel.context = context
        best = max(cand_wheels)
        assert_equal(list(best.tags)[0], supp[0])
        
        # assert_equal(
        #     list(map(get_tags, pick_best(cand_wheels, supp, top=False))), supp)


if __name__ == '__main__':
    import nose
    nose.main()
