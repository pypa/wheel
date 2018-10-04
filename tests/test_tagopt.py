"""
Tests for the bdist_wheel tag options (--python-tag, --universal, and
--plat-name)
"""

import os
import subprocess
import sys
import zipfile

import pytest

SETUP_PY = """\
from setuptools import setup, Extension

setup(
    name="Test",
    version="1.0",
    author_email="author@example.com",
    py_modules=["test"],
    {ext_modules}
)
"""

EXT_MODULES = "ext_modules=[Extension('_test', sources=['test.c'])],"


@pytest.fixture
def temp_pkg(request, tmpdir):
    tmpdir.join('test.py').write('print("Hello, world")')

    ext = getattr(request, 'param', False)
    if ext:
        tmpdir.join('test.c').write('#include <stdio.h>')
        setup_py = SETUP_PY.format(ext_modules=EXT_MODULES)
    else:
        setup_py = SETUP_PY.format(ext_modules='')

    tmpdir.join('setup.py').write(setup_py)
    return tmpdir


def test_default_tag(temp_pkg):
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel'], cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename == 'Test-1.0-py%s-none-any.whl' % (sys.version[0],)
    assert wheels[0].ext == '.whl'


def test_build_number(temp_pkg):
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel', '--build-number=1'],
                          cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert (wheels[0].basename == 'Test-1.0-1-py%s-none-any.whl' % (sys.version[0],))
    assert wheels[0].ext == '.whl'
    with zipfile.ZipFile(str(wheels[0])) as wheel:
        distinfo_dirs = set(filter(None, (os.path.split(x)[0] for x in wheel.namelist())))
    assert len(distinfo_dirs) == 1


def test_explicit_tag(temp_pkg):
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel', '--python-tag=py32'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.startswith('Test-1.0-py32-')
    assert wheels[0].ext == '.whl'


def test_universal_tag(temp_pkg):
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel', '--universal'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.startswith('Test-1.0-py2.py3-')
    assert wheels[0].ext == '.whl'


def test_universal_beats_explicit_tag(temp_pkg):
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel', '--universal', '--python-tag=py32'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.startswith('Test-1.0-py2.py3-')
    assert wheels[0].ext == '.whl'


def test_universal_in_setup_cfg(temp_pkg):
    temp_pkg.join('setup.cfg').write('[bdist_wheel]\nuniversal=1')
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.startswith('Test-1.0-py2.py3-')
    assert wheels[0].ext == '.whl'


def test_pythontag_in_setup_cfg(temp_pkg):
    temp_pkg.join('setup.cfg').write('[bdist_wheel]\npython_tag=py32')
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.startswith('Test-1.0-py32-')
    assert wheels[0].ext == '.whl'


def test_legacy_wheel_section_in_setup_cfg(temp_pkg):
    temp_pkg.join('setup.cfg').write('[wheel]\nuniversal=1')
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.startswith('Test-1.0-py2.py3-')
    assert wheels[0].ext == '.whl'


def test_plat_name_purepy(temp_pkg):
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel', '--plat-name=testplat.pure'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.endswith('-testplat_pure.whl')
    assert wheels[0].ext == '.whl'


@pytest.mark.parametrize('temp_pkg', [True], indirect=['temp_pkg'])
def test_plat_name_ext(temp_pkg):
    try:
        subprocess.check_call(
            [sys.executable, 'setup.py', 'bdist_wheel', '--plat-name=testplat.arch'],
            cwd=str(temp_pkg))
    except subprocess.CalledProcessError:
        pytest.skip("Cannot compile C Extensions")

    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.endswith('-testplat_arch.whl')
    assert wheels[0].ext == '.whl'


def test_plat_name_purepy_in_setupcfg(temp_pkg):
    temp_pkg.join('setup.cfg').write('[bdist_wheel]\nplat_name=testplat.pure')
    subprocess.check_call(
        [sys.executable, 'setup.py', 'bdist_wheel'],
        cwd=str(temp_pkg))
    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.endswith('-testplat_pure.whl')
    assert wheels[0].ext == '.whl'


@pytest.mark.parametrize('temp_pkg', [True], indirect=['temp_pkg'])
def test_plat_name_ext_in_setupcfg(temp_pkg):
    temp_pkg.join('setup.cfg').write('[bdist_wheel]\nplat_name=testplat.arch')
    try:
        subprocess.check_call(
            [sys.executable, 'setup.py', 'bdist_wheel'],
            cwd=str(temp_pkg))
    except subprocess.CalledProcessError:
        pytest.skip("Cannot compile C Extensions")

    dist_dir = temp_pkg.join('dist')
    assert dist_dir.check(dir=1)
    wheels = dist_dir.listdir()
    assert len(wheels) == 1
    assert wheels[0].basename.endswith('-testplat_arch.whl')
    assert wheels[0].ext == '.whl'
