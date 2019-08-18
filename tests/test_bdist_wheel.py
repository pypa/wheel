# coding: utf-8
import os
import subprocess
import sys
from zipfile import ZipFile

import pytest

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


@pytest.fixture(scope='module')
def dummy_dist(tmpdir_factory):
    basedir = tmpdir_factory.mktemp('dummy_dist')
    basedir.join('setup.py').write("""\
from setuptools import setup

setup(
    name='dummy_dist',
    version='1.0'
)
""")
    for fname in DEFAULT_LICENSE_FILES:
        basedir.join(fname).write('')

    basedir.join('licenses').mkdir().join('DUMMYFILE').write('')
    return basedir


def test_no_scripts(wheel_paths):
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if 'complex_dist' in path)
    for entry in ZipFile(path).infolist():
        assert '.data/scripts/' not in entry.filename


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


def test_limited_abi(monkeypatch, tmpdir):
    """Test that building a binary wheel with the limited ABI works."""
    this_dir = os.path.dirname(__file__)
    source_dir = os.path.join(this_dir, 'testdata', 'extension.dist')
    build_dir = tmpdir.join('build')
    dist_dir = tmpdir.join('dist')
    monkeypatch.chdir(source_dir)
    subprocess.check_call([sys.executable, 'setup.py',  'bdist_wheel', '-b', str(build_dir),
                           '-d', str(dist_dir)])
