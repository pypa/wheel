# Test wheel.
# The file has the following contents:
#   hello.pyd
#   hello/hello.py
#   hello/__init__.py
#   test-1.0.data/data/hello.dat
#   test-1.0.data/headers/hello.dat
#   test-1.0.data/scripts/hello.sh
#   test-1.0.dist-info/WHEEL
#   test-1.0.dist-info/METADATA
#   test-1.0.dist-info/RECORD
# The root is PLATLIB
# So, some in PLATLIB, and one in each of DATA, HEADERS and SCRIPTS.

import os
import shutil
from tempfile import mkdtemp

import wheel.pep425tags
import wheel.tool
from wheel.install import WheelFile

THISDIR = os.path.dirname(__file__)
TESTWHEEL = os.path.join(THISDIR, 'test-1.0-py2.py3-none-win32.whl')


def test_compatibility_tags():
    """Test compatibilty tags are working."""
    wf = WheelFile("package-1.0.0-cp32.cp33-noabi-noarch.whl")
    assert (list(wf.compatibility_tags) ==
            [('cp32', 'noabi', 'noarch'), ('cp33', 'noabi', 'noarch')])
    assert wf.arity == 2

    wf2 = WheelFile("package-1.0.0-1st-cp33-noabi-noarch.whl")
    wf2_info = wf2.parsed_filename.groupdict()
    assert wf2_info['build'] == '1st', wf2_info


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
        def context():
            return list(supp)

        for wheel_ in cand_wheels:
            wheel_.context = context
        best = max(cand_wheels)
        assert list(best.tags)[0] == supp[0]

        # assert_equal(
        #     list(map(get_tags, pick_best(cand_wheels, supp, top=False))), supp)


def test_install():
    def check(*path):
        return os.path.exists(os.path.join(*path))

    def get_supported():
        return list(wheel.pep425tags.get_supported()) + [('py3', 'none', 'win32')]

    tempdir = mkdtemp()
    whl = WheelFile(TESTWHEEL, context=get_supported)
    assert whl.supports_current_python(get_supported)
    try:
        locs = {}
        for key in ('purelib', 'platlib', 'scripts', 'headers', 'data'):
            locs[key] = os.path.join(tempdir, key)
            os.mkdir(locs[key])
        whl.install(overrides=locs)
        assert len(os.listdir(locs['purelib'])) == 0
        assert check(locs['platlib'], 'hello.pyd')
        assert check(locs['platlib'], 'hello', 'hello.py')
        assert check(locs['platlib'], 'hello', '__init__.py')
        assert check(locs['data'], 'hello.dat')
        assert check(locs['headers'], 'hello.dat')
        assert check(locs['scripts'], 'hello.sh')
        assert check(locs['platlib'], 'test-1.0.dist-info', 'RECORD')
    finally:
        shutil.rmtree(tempdir)


def test_install_tool():
    """Slightly improve coverage of wheel.install"""
    wheel.tool.install([TESTWHEEL], force=True, dry_run=True)


def test_wheelfile_re():
    # Regression test for #208
    wf = WheelFile('foo-2-py3-none-any.whl')
    assert wf.distinfo_name == 'foo-2.dist-info'
