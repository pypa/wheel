# coding: utf-8
import os.path
import shutil
import stat
import subprocess
import sys
from zipfile import ZipFile

import pytest

from wheel.bdist_wheel import bdist_wheel
from wheel.wheelfile import WheelFile

DEFAULT_FILES = {
    'dummy_dist-1.0.dist-info/top_level.txt',
    'dummy_dist-1.0.dist-info/METADATA',
    'dummy_dist-1.0.dist-info/WHEEL',
    'dummy_dist-1.0.dist-info/RECORD'
}
DEFAULT_LICENSE_FILES = {
    'LICENSE', 'LICENSE.txt', 'LICENCE', 'LICENCE.txt', 'COPYING',
    'COPYING.md', 'NOTICE', 'NOTICE.rst', 'AUTHORS', 'AUTHORS.txt'
}
OTHER_IGNORED_FILES = {
    'LICENSE~', 'AUTHORS~',
}


@pytest.fixture
def dummy_dist(tmpdir_factory):
    basedir = tmpdir_factory.mktemp('dummy_dist')
    basedir.join('setup.py').write("""\
from setuptools import setup

setup(
    name='dummy_dist',
    version='1.0'
)
""")
    for fname in DEFAULT_LICENSE_FILES | OTHER_IGNORED_FILES:
        basedir.join(fname).write('')

    basedir.join('licenses').mkdir().join('DUMMYFILE').write('')
    return basedir


def test_no_scripts(wheel_paths):
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if 'complex_dist' in path)
    for entry in ZipFile(path).infolist():
        assert '.data/scripts/' not in entry.filename


@pytest.mark.skipif(sys.version_info < (3, 6),
                    reason='Packaging unicode file names only works reliably on Python 3.6+')
def test_unicode_record(wheel_paths):
    path = next(path for path in wheel_paths if 'unicode.dist' in path)
    with ZipFile(path) as zf:
        record = zf.read('unicode.dist-0.1.dist-info/RECORD')

    assert u'åäö_日本語.py'.encode('utf-8') in record


def test_licenses_default(dummy_dist, monkeypatch, tmpdir):
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel', '-b', str(tmpdir),
                           '--universal'])
    with WheelFile('dist/dummy_dist-1.0-py2.py3-none-any.whl') as wf:
        license_files = {'dummy_dist-1.0.dist-info/' + fname for fname in DEFAULT_LICENSE_FILES}
        assert set(wf.namelist()) == DEFAULT_FILES | license_files


def test_licenses_deprecated(dummy_dist, monkeypatch, tmpdir):
    dummy_dist.join('setup.cfg').write('[metadata]\nlicense_file=licenses/DUMMYFILE')
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel', '-b', str(tmpdir),
                           '--universal'])
    with WheelFile('dist/dummy_dist-1.0-py2.py3-none-any.whl') as wf:
        license_files = {'dummy_dist-1.0.dist-info/DUMMYFILE'}
        assert set(wf.namelist()) == DEFAULT_FILES | license_files


def test_licenses_override(dummy_dist, monkeypatch, tmpdir):
    dummy_dist.join('setup.cfg').write('[metadata]\nlicense_files=licenses/*\n  LICENSE')
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel', '-b', str(tmpdir),
                           '--universal'])
    with WheelFile('dist/dummy_dist-1.0-py2.py3-none-any.whl') as wf:
        license_files = {'dummy_dist-1.0.dist-info/' + fname for fname in {'DUMMYFILE', 'LICENSE'}}
        assert set(wf.namelist()) == DEFAULT_FILES | license_files


def test_licenses_disabled(dummy_dist, monkeypatch, tmpdir):
    dummy_dist.join('setup.cfg').write('[metadata]\nlicense_files=\n')
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel', '-b', str(tmpdir),
                           '--universal'])
    with WheelFile('dist/dummy_dist-1.0-py2.py3-none-any.whl') as wf:
        assert set(wf.namelist()) == DEFAULT_FILES


def test_build_number(dummy_dist, monkeypatch, tmpdir):
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel', '-b', str(tmpdir),
                           '--universal', '--build-number=2'])
    with WheelFile('dist/dummy_dist-1.0-2-py2.py3-none-any.whl') as wf:
        filenames = set(wf.namelist())
        assert 'dummy_dist-1.0.dist-info/RECORD' in filenames
        assert 'dummy_dist-1.0.dist-info/METADATA' in filenames


@pytest.mark.skipif(sys.version_info[0] < 3, reason='The limited ABI only works on Python 3+')
def test_limited_abi(monkeypatch, tmpdir):
    """Test that building a binary wheel with the limited ABI works."""
    this_dir = os.path.dirname(__file__)
    source_dir = os.path.join(this_dir, 'testdata', 'extension.dist')
    build_dir = tmpdir.join('build')
    dist_dir = tmpdir.join('dist')
    monkeypatch.chdir(source_dir)
    subprocess.check_call([sys.executable, 'setup.py',  'bdist_wheel', '-b', str(build_dir),
                           '-d', str(dist_dir)])


def test_build_from_readonly_tree(dummy_dist, monkeypatch, tmpdir):
    basedir = str(tmpdir.join('dummy'))
    shutil.copytree(str(dummy_dist), basedir)
    monkeypatch.chdir(basedir)

    # Make the tree read-only
    for root, dirs, files in os.walk(basedir):
        for fname in files:
            os.chmod(os.path.join(root, fname), stat.S_IREAD)

    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel'])


@pytest.mark.parametrize('option, compress_type', list(bdist_wheel.supported_compressions.items()),
                         ids=list(bdist_wheel.supported_compressions))
def test_compression(dummy_dist, monkeypatch, tmpdir, option, compress_type):
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call([sys.executable, 'setup.py', 'bdist_wheel', '-b', str(tmpdir),
                           '--universal', '--compression={}'.format(option)])
    with WheelFile('dist/dummy_dist-1.0-py2.py3-none-any.whl') as wf:
        filenames = set(wf.namelist())
        assert 'dummy_dist-1.0.dist-info/RECORD' in filenames
        assert 'dummy_dist-1.0.dist-info/METADATA' in filenames
        for zinfo in wf.filelist:
            assert zinfo.compress_type == compress_type


def test_wheelfile_line_endings(wheel_paths):
    for path in wheel_paths:
        with WheelFile(path) as wf:
            wheelfile = next(fn for fn in wf.filelist if fn.filename.endswith('WHEEL'))
            wheelfile_contents = wf.read(wheelfile)
            assert b'\r' not in wheelfile_contents
