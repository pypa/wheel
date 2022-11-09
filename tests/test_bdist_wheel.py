from __future__ import annotations

import os.path
import shutil
import stat
import subprocess
import sys
import sysconfig
from zipfile import ZipFile

import pytest

from wheel.bdist_wheel import bdist_wheel, get_abi_tag
from wheel.vendored.packaging import tags
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
def dummy_dist(tmpdir_factory):
    basedir = tmpdir_factory.mktemp("dummy_dist")
    basedir.join("setup.py").write(SETUPPY_EXAMPLE)
    for fname in DEFAULT_LICENSE_FILES | OTHER_IGNORED_FILES:
        basedir.join(fname).write("")

    basedir.join("licenses").mkdir().join("DUMMYFILE").write("")
    return basedir


def test_no_scripts(wheel_paths):
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if "complex_dist" in path)
    for entry in ZipFile(path).infolist():
        assert ".data/scripts/" not in entry.filename


def test_unicode_record(wheel_paths):
    path = next(path for path in wheel_paths if "unicode.dist" in path)
    with ZipFile(path) as zf:
        record = zf.read("unicode.dist-0.1.dist-info/RECORD")

    assert "åäö_日本語.py".encode() in record


UTF8_PKG_INFO = """\
Metadata-Version: 2.1
Name: helloworld
Version: 42
Author-email: "John X. Ãørçeč" <john@utf8.org>, Γαμα קּ 東 <gama@utf8.org>


UTF-8 描述 説明
"""


def test_preserve_unicode_metadata(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    egginfo = tmp_path / "dummy_dist.egg-info"
    distinfo = tmp_path / "dummy_dist.dist-info"

    egginfo.mkdir()
    (egginfo / "PKG-INFO").write_text(UTF8_PKG_INFO, encoding="utf-8")
    (egginfo / "dependency_links.txt").touch()

    class simpler_bdist_wheel(bdist_wheel):
        """Avoid messing with setuptools/distutils internals"""

        def __init__(self):
            pass

        @property
        def license_paths(self):
            return []

    cmd_obj = simpler_bdist_wheel()
    cmd_obj.egg2dist(egginfo, distinfo)

    metadata = (distinfo / "METADATA").read_text(encoding="utf-8")
    assert 'Author-email: "John X. Ãørçeč"' in metadata
    assert "Γαμα קּ 東 " in metadata
    assert "UTF-8 描述 説明" in metadata


def test_licenses_default(dummy_dist, monkeypatch, tmpdir):
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmpdir), "--universal"]
    )
    with WheelFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        license_files = {
            "dummy_dist-1.0.dist-info/" + fname for fname in DEFAULT_LICENSE_FILES
        }
        assert set(wf.namelist()) == DEFAULT_FILES | license_files


def test_licenses_deprecated(dummy_dist, monkeypatch, tmpdir):
    dummy_dist.join("setup.cfg").write("[metadata]\nlicense_file=licenses/DUMMYFILE")
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmpdir), "--universal"]
    )
    with WheelFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        license_files = {"dummy_dist-1.0.dist-info/DUMMYFILE"}
        assert set(wf.namelist()) == DEFAULT_FILES | license_files


@pytest.mark.parametrize(
    "config_file, config",
    [
        ("setup.cfg", "[metadata]\nlicense_files=licenses/*\n  LICENSE"),
        ("setup.cfg", "[metadata]\nlicense_files=licenses/*, LICENSE"),
        (
            "setup.py",
            SETUPPY_EXAMPLE.replace(
                ")", "  license_files=['licenses/DUMMYFILE', 'LICENSE'])"
            ),
        ),
    ],
)
def test_licenses_override(dummy_dist, monkeypatch, tmpdir, config_file, config):
    dummy_dist.join(config_file).write(config)
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmpdir), "--universal"]
    )
    with WheelFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        license_files = {
            "dummy_dist-1.0.dist-info/" + fname for fname in {"DUMMYFILE", "LICENSE"}
        }
        assert set(wf.namelist()) == DEFAULT_FILES | license_files


def test_licenses_disabled(dummy_dist, monkeypatch, tmpdir):
    dummy_dist.join("setup.cfg").write("[metadata]\nlicense_files=\n")
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmpdir), "--universal"]
    )
    with WheelFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        assert set(wf.namelist()) == DEFAULT_FILES


def test_build_number(dummy_dist, monkeypatch, tmpdir):
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
    with WheelFile("dist/dummy_dist-1.0-2-py2.py3-none-any.whl") as wf:
        filenames = set(wf.namelist())
        assert "dummy_dist-1.0.dist-info/RECORD" in filenames
        assert "dummy_dist-1.0.dist-info/METADATA" in filenames


def test_limited_abi(monkeypatch, tmpdir):
    """Test that building a binary wheel with the limited ABI works."""
    this_dir = os.path.dirname(__file__)
    source_dir = os.path.join(this_dir, "testdata", "extension.dist")
    build_dir = tmpdir.join("build")
    dist_dir = tmpdir.join("dist")
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


def test_build_from_readonly_tree(dummy_dist, monkeypatch, tmpdir):
    basedir = str(tmpdir.join("dummy"))
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
def test_compression(dummy_dist, monkeypatch, tmpdir, option, compress_type):
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [
            sys.executable,
            "setup.py",
            "bdist_wheel",
            "-b",
            str(tmpdir),
            "--universal",
            f"--compression={option}",
        ]
    )
    with WheelFile("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        filenames = set(wf.namelist())
        assert "dummy_dist-1.0.dist-info/RECORD" in filenames
        assert "dummy_dist-1.0.dist-info/METADATA" in filenames
        for zinfo in wf.filelist:
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


def test_get_abi_tag_old(monkeypatch):
    monkeypatch.setattr(tags, "interpreter_name", lambda: "pp")
    monkeypatch.setattr(sysconfig, "get_config_var", lambda x: "pypy36-pp73")
    assert get_abi_tag() == "pypy36_pp73"


def test_get_abi_tag_new(monkeypatch):
    monkeypatch.setattr(sysconfig, "get_config_var", lambda x: "pypy37-pp73-darwin")
    monkeypatch.setattr(tags, "interpreter_name", lambda: "pp")
    assert get_abi_tag() == "pypy37_pp73"
