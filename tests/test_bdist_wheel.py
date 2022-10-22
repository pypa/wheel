from __future__ import annotations

import os.path
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest
from _pytest.monkeypatch import MonkeyPatch
from _pytest.tmpdir import TempPathFactory

from wheel.bdist_wheel import bdist_wheel
from wheel.wheelfile import WheelFile

DEFAULT_FILES = {
    "dummy_dist-1.0.dist-info/top_level.txt",
    "dummy_dist-1.0.dist-info/METADATA",
    "dummy_dist-1.0.dist-info/WHEEL",
    "dummy_dist-1.0.dist-info/RECORD",
}
DEFAULT_LICENSE_FILES = {
    "LICENSE",
    "LICENSE.txt",
    "LICENCE",
    "LICENCE.txt",
    "COPYING",
    "COPYING.md",
    "NOTICE",
    "NOTICE.rst",
    "AUTHORS",
    "AUTHORS.txt",
}
OTHER_IGNORED_FILES = {
    "LICENSE~",
    "AUTHORS~",
}
SETUPPY_EXAMPLE = """\
from setuptools import setup

setup(
    name='dummy_dist',
    version='1.0',
)
"""


@pytest.fixture
def dummy_dist(tmp_path_factory: TempPathFactory) -> Path:
    basedir = tmp_path_factory.mktemp('dummy_dist')
    basedir.joinpath('setup.py').write_text(SETUPPY_EXAMPLE)
    for fname in DEFAULT_LICENSE_FILES | OTHER_IGNORED_FILES:
        basedir.joinpath(fname).write_text("")

    licenses_path = basedir.joinpath("licenses")
    licenses_path.mkdir()
    licenses_path.joinpath("DUMMYFILE").write_text("")
    return basedir


def test_no_scripts(wheel_paths):
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if "complex_dist" in path.name)
    with WheelFile(path) as wf:
        filenames = set(wf.filenames)

    for filename in filenames:
        assert ".data/scripts/" not in filename


def test_unicode_record(wheel_paths):
    path = next(path for path in wheel_paths if "unicode.dist" in path)
    with ZipFile(path) as zf:
        record = zf.read("unicode.dist-0.1.dist-info/RECORD")

    assert "åäö_日本語.py".encode() in record


def test_licenses_default(dummy_dist, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmp_path), "--universal"]
    )
    with WheelFile('dist/dummy_dist-1.0-py2.py3-none-any.whl') as wf:
        license_files = {
            "dummy_dist-1.0.dist-info/" + fname for fname in DEFAULT_LICENSE_FILES
        }
        assert set(wf.filenames) == DEFAULT_FILES | license_files


def test_licenses_deprecated(dummy_dist, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    dummy_dist.joinpath('setup.cfg').write_text('[metadata]\nlicense_file=licenses/DUMMYFILE')
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmp_path), "--universal"]
    )
    with WheelFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        license_files = {'dummy_dist-1.0.dist-info/DUMMYFILE'}
        assert set(wf.filenames) == DEFAULT_FILES | license_files


def test_licenses_disabled(dummy_dist, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    dummy_dist.joinpath("setup.cfg").write_text("[metadata]\nlicense_files=\n")
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmp_path), "--universal"]
    )
    with WheelFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        assert set(wf.filenames) == DEFAULT_FILES


def test_build_number(dummy_dist, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "-b",
            str(tmp_path),
            "--universal",
            "--build-number=2",
        ]
    )
    with WheelFile("dist/dummy_dist-1.0-2-py2.py3-none-any.whl") as wf:
        filenames = set(wf.filenames)
        assert "dummy_dist-1.0.dist-info/RECORD" in filenames
        assert "dummy_dist-1.0.dist-info/METADATA" in filenames


def test_limited_abi(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test that building a binary wheel with the limited ABI works."""
    this_dir = os.path.dirname(__file__)
    source_dir = os.path.join(this_dir, 'testdata', 'extension.dist')
    build_dir = tmp_path / 'build'
    dist_dir = tmp_path / 'dist'
    monkeypatch.chdir(source_dir)
    subprocess.check_call(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "-b",
            str(build_dir),
            "-d",
            str(dist_dir),
        ]
    )


def test_build_from_readonly_tree(dummy_dist, monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    basedir = str(tmp_path / 'dummy')
    shutil.copytree(str(dummy_dist), basedir)
    monkeypatch.chdir(basedir)

    # Make the tree read-only
    for root, _dirs, files in os.walk(basedir):
        for fname in files:
            os.chmod(os.path.join(root, fname), stat.S_IREAD)

    subprocess.check_call([sys.executable, "setup.py", "bdist_wheel"])


@pytest.mark.parametrize(
    "option, compress_type",
    list(bdist_wheel.supported_compressions.items()),
    ids=list(bdist_wheel.supported_compressions),
)
def test_compression(dummy_dist, monkeypatch: MonkeyPatch, tmp_path: Path, option, compress_type):
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "-b",
            str(tmp_path),
            "--universal",
            f"--compression={option}",
        ]
    )
    with ZipFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as zf:
        filenames = set(zf.namelist())
        assert "dummy_dist-1.0.dist-info/RECORD" in filenames
        assert "dummy_dist-1.0.dist-info/METADATA" in filenames
        for zinfo in zf.infolist():
            assert zinfo.compress_type == compress_type


def test_wheelfile_line_endings(wheel_paths):
    for path in wheel_paths:
        with WheelFile(path) as wf:
            wheelfile = next(fn for fn in wf.filelist if fn.filename.endswith("WHEEL"))
            wheelfile_contents = wf.read(wheelfile)
            assert b"\r" not in wheelfile_contents


def test_unix_epoch_timestamps(dummy_dist, monkeypatch, tmpdir):
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "-b",
            str(tmpdir),
            "--universal",
            "--build-number=2",
        ]
    )
