from __future__ import annotations

import os.path
import shutil
import stat
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path, PurePath
from zipfile import ZipFile

import pytest
from pytest import MonkeyPatch, TempPathFactory

from wheel import WheelReader
from wheel.bdist_wheel import get_abi_tag
from wheel.vendored.packaging import tags

DEFAULT_FILES = {
    PurePath("dummy-dist-1.0.dist-info/top_level.txt"),
    PurePath("dummy-dist-1.0.dist-info/METADATA"),
    PurePath("dummy-dist-1.0.dist-info/WHEEL"),
    PurePath("dummy-dist-1.0.dist-info/RECORD"),
}
DEFAULT_LICENSE_FILES = {
    PurePath("LICENSE"),
    PurePath("LICENSE.txt"),
    PurePath("LICENCE"),
    PurePath("LICENCE.txt"),
    PurePath("COPYING"),
    PurePath("COPYING.md"),
    PurePath("NOTICE"),
    PurePath("NOTICE.rst"),
    PurePath("AUTHORS"),
    PurePath("AUTHORS.txt"),
}
OTHER_IGNORED_FILES = {
    PurePath("LICENSE~"),
    PurePath("AUTHORS~"),
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
    basedir = tmp_path_factory.mktemp("dummy_dist")
    basedir.joinpath("setup.py").write_text(SETUPPY_EXAMPLE)
    for fname in DEFAULT_LICENSE_FILES | OTHER_IGNORED_FILES:
        basedir.joinpath(fname).write_text("")

    licenses_path = basedir.joinpath("licenses")
    licenses_path.mkdir()
    licenses_path.joinpath("DUMMYFILE").write_text("")
    return basedir


def test_no_scripts(wheel_paths: list[Path]) -> None:
    """Make sure entry point scripts are not generated."""
    path = next(path for path in wheel_paths if "complex_dist" in path.name)
    with WheelReader(path) as wf:
        filenames = set(wf.filenames)

    for filename in filenames:
        assert ".data/scripts/" not in filename.name


def test_unicode_record(wheel_paths: list[Path]) -> None:
    path = next(path for path in wheel_paths if "unicode.dist" in path.name)
    with WheelReader(path) as wf:
        record = wf.read_dist_info("RECORD")

    assert "åäö_日本語.py" in record


def test_unicode_metadata(wheel_paths: list[Path]) -> None:
    path = next(path for path in wheel_paths if "unicode.dist" in path.name)
    with WheelReader(path) as wf:
        metadata = wf.read_dist_info("METADATA")

    assert "Summary: A testing distribution ☃" in metadata


def test_licenses_default(
    dummy_dist: Path, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmp_path), "--universal"]
    )
    with WheelReader("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        license_files = {
            PurePath("dummy-dist-1.0.dist-info/") / fname
            for fname in DEFAULT_LICENSE_FILES
        }
        assert set(wf.filenames) == DEFAULT_FILES | license_files


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
def test_licenses_override(
    dummy_dist: Path,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    config_file: str,
    config: str,
) -> None:
    dummy_dist.joinpath(config_file).write_text(config)
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmp_path), "--universal"]
    )
    with WheelReader("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        license_files = {
            PurePath("dummy-dist-1.0.dist-info") / fname
            for fname in {"DUMMYFILE", "LICENSE"}
        }
        assert set(wf.filenames) == DEFAULT_FILES | license_files


def test_licenses_disabled(
    dummy_dist: Path, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    dummy_dist.joinpath("setup.cfg").write_text("[metadata]\nlicense_files=\n")
    monkeypatch.chdir(dummy_dist)
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "-b", str(tmp_path), "--universal"]
    )
    with WheelReader("dist/dummy_dist-1.0-py2.py3-none-any.whl") as wf:
        assert set(wf.filenames) == DEFAULT_FILES


def test_build_number(
    dummy_dist: Path, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
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
    with WheelReader("dist/dummy_dist-1.0-2-py2.py3-none-any.whl") as wf:
        filenames = set(wf.filenames)
        assert PurePath("dummy-dist-1.0.dist-info/RECORD") in filenames
        assert PurePath("dummy-dist-1.0.dist-info/METADATA") in filenames


def test_limited_abi(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """Test that building a binary wheel with the limited ABI works."""
    this_dir = os.path.dirname(__file__)
    source_dir = os.path.join(this_dir, "testdata", "extension.dist")
    build_dir = tmp_path / "build"
    dist_dir = tmp_path / "dist"
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


def test_build_from_readonly_tree(
    dummy_dist: Path, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    basedir = str(tmp_path / "dummy")
    shutil.copytree(str(dummy_dist), basedir)
    monkeypatch.chdir(basedir)

    # Make the tree read-only
    for root, _dirs, files in os.walk(basedir):
        for fname in files:
            os.chmod(os.path.join(root, fname), stat.S_IREAD)

    subprocess.check_call([sys.executable, "setup.py", "bdist_wheel"])


@pytest.mark.parametrize(
    "option, compress_type",
    [
        pytest.param("stored", zipfile.ZIP_STORED, id="stored"),
        pytest.param("deflated", zipfile.ZIP_DEFLATED, id="deflated"),
    ],
)
def test_compression(
    dummy_dist: Path,
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    option: str,
    compress_type: int,
) -> None:
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
        for zinfo in zf.infolist():
            assert zinfo.compress_type == compress_type


def test_wheelfile_line_endings(wheel_paths: list[Path]) -> None:
    for path in wheel_paths:
        with WheelReader(path) as wf:
            wheelfile_contents = wf.read_dist_info("WHEEL")
            assert "\r" not in wheelfile_contents


def test_unix_epoch_timestamps(
    dummy_dist: Path, monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "0")
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


def test_get_abi_tag_old(monkeypatch):
    monkeypatch.setattr(tags, "interpreter_name", lambda: "pp")
    monkeypatch.setattr(sysconfig, "get_config_var", lambda x: "pypy36-pp73")
    assert get_abi_tag() == "pypy36_pp73"


def test_get_abi_tag_new(monkeypatch):
    monkeypatch.setattr(sysconfig, "get_config_var", lambda x: "pypy37-pp73-darwin")
    monkeypatch.setattr(tags, "interpreter_name", lambda: "pp")
    assert get_abi_tag() == "pypy37_pp73"
