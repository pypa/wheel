"""
Basic wheel tests.
"""

import os
import pkg_resources
import json
import sys

from pkg_resources import resource_filename

import wheel.util
from wheel import egg2wheel
from wheel.install import WheelFile
from zipfile import ZipFile
from shutil import rmtree

test_distributions = ("simple.dist", "complex-dist", "headers.dist")

def teardown_module():
    """Delete eggs/wheels created by tests."""
    base = pkg_resources.resource_filename('wheel.test', '')
    for dist in test_distributions:
        for subdir in ('build', 'dist'):
            try:
                rmtree(os.path.join(base, dist, subdir))
            except OSError:
                pass
                        
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
    assert (list(wf.compatibility_tags) ==
                 [('cp32', 'noabi', 'noarch'), ('cp33', 'noabi', 'noarch')])
    assert (wf.arity == 2)

    wf2 = WheelFile("package-1.0.0-1st-cp33-noabi-noarch.whl")
    wf2_info = wf2.parsed_filename.groupdict()
    assert wf2_info['build'] == '1st', wf2_info


def test_bdist_wheel():
    """Make sure bdist_wheel finish without errors."""
    for dist in test_distributions:
        pwd = os.curdir
        simpledist = pkg_resources.resource_filename('wheel.test', dist)
        os.chdir(simpledist)    
        try:
            sys.argv = ['', 'bdist_wheel']
            exec(compile(open('setup.py').read(), 'setup.py', 'exec'))
        finally:
            os.chdir(pwd)
            
def test_convert_egg():
    """Convert some eggs to wheels."""
    for dist in ("simple.dist", "complex-dist", "headers.dist"):
        pwd = os.curdir
        simpledist = pkg_resources.resource_filename('wheel.test', dist)
        os.chdir(simpledist)
        try:
            sys.argv = ['', 'bdist_egg']
            exec(compile(open('setup.py').read(), 'setup.py', 'exec'))
        finally:
            os.chdir(pwd)

def test_pymeta():
    """Make sure pymeta.json exists and validates against our schema."""
    # XXX this test may need manual cleanup of older wheels
    
    import jsonschema
    
    def open_json(filename):
        return json.loads(open(filename, 'rb').read().decode('utf-8'))
    
    pymeta_schema = open_json(resource_filename('wheel.test',
                                                'pymeta-schema.json'))
    valid = 0
    for dist in ("simple.dist", "complex-dist"):
        basedir = pkg_resources.resource_filename('wheel.test', dist)
        for (dirname, subdirs, filenames) in os.walk(basedir):
            for filename in filenames:
                if filename.endswith('.whl'):
                    whl = ZipFile(os.path.join(dirname, filename))
                    for entry in whl.infolist():
                        if entry.filename.endswith('/pymeta.json'):
                            pymeta = json.loads(whl.read(entry).decode('utf-8'))
                            jsonschema.validate(pymeta, pymeta_schema)
                            valid += 1
    assert valid > 0, "No pymeta.json found"

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
        assert list(best.tags)[0] == supp[0]
        
        # assert_equal(
        #     list(map(get_tags, pick_best(cand_wheels, supp, top=False))), supp)
