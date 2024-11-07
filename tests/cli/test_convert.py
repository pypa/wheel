from __future__ import annotations

import os.path
import zipfile
from pathlib import Path
from textwrap import dedent

import pytest
from _pytest.fixtures import SubRequest
from pytest import TempPathFactory

import wheel
from wheel.cli.convert import convert, egg_filename_re
from wheel.wheelfile import WHEEL_INFO_RE, WheelFile

PKG_INFO = dedent(
    """\
    Metadata-Version: 2.1
    Name: Sampledist
    Version: 1.0.0
    Author: Alex Grönholm
    Author-email: alex.gronholm@example.com
    Description: Sample Distribution
        ===================
          Test description
    """
)
EXPECTED_METADATA = dedent(
    """\
    Metadata-Version: 2.4
    Name: Sampledist
    Version: 1.0.0
    Author: Alex Grönholm
    Author-email: alex.gronholm@example.com

    Sample Distribution
    ===================
      Test description

    """
).encode("utf-8")


@pytest.fixture(
    params=[
        pytest.param(("py3.7", "win32"), id="win32"),
        pytest.param(("py3.7", "win_amd64"), id="amd64"),
        pytest.param((None, "any"), id="pure"),
    ]
)
def pyver_arch(request: SubRequest) -> tuple[str | None, str]:
    return request.param


@pytest.fixture
def pyver(pyver_arch: tuple[str | None, str]) -> str | None:
    return pyver_arch[0]


@pytest.fixture
def arch(pyver_arch: tuple[str | None, str]) -> str:
    return pyver_arch[1]


@pytest.fixture
def expected_wheelfile(arch: str) -> bytes:
    root_is_purelib = str(arch == "any").lower()
    text = dedent(
        f"""\
        Wheel-Version: 1.0
        Generator: wheel {wheel.__version__}
        Root-Is-Purelib: {root_is_purelib}
        """
    )
    if arch == "any":
        text += "Tag: py2-none-any\nTag: py3-none-any\n\n"
    else:
        text += f"Tag: py37-cp37-{arch}\n\n"

    return text.encode("utf-8")


@pytest.fixture
def bdist_wininst_path(arch: str, pyver: str | None, tmp_path: Path) -> str:
    # As bdist_wininst is no longer present in Python, and carrying .exe files in the
    # tarball is risky, we have to fake this a bit
    if pyver:
        filename = f"Sampledist-1.0.0-{arch.replace('_', '-')}-{pyver}.exe"
        pyver_suffix = f"-{pyver}"
    else:
        filename = f"Sampledist-1.0.0-{arch.replace('_', '-')}.exe"
        pyver_suffix = ""

    bdist_path = tmp_path / filename
    prefix = "PURELIB" if arch == "any" else "PLATLIB"
    with zipfile.ZipFile(bdist_path, "w") as zip:
        zip.writestr(f"{prefix}/", b"")
        zip.writestr(f"{prefix}/sampledist/", b"")
        zip.writestr(f"{prefix}/Sampledist-1.0.0{pyver_suffix}.egg-info/", b"")
        zip.writestr(f"{prefix}/sampledist/__init__.py", b"")
        if arch != "any":
            zip.writestr(f"{prefix}/sampledist/_extmodule.cp37-{arch}.pyd", b"")

        zip.writestr(
            f"{prefix}/Sampledist-1.0.0{pyver_suffix}.egg-info/dependency_links.txt",
            b"",
        )
        zip.writestr(
            f"{prefix}/Sampledist-1.0.0{pyver_suffix}.egg-info/PKG-INFO",
            PKG_INFO.encode("utf-8"),
        )
        zip.writestr(
            f"{prefix}/Sampledist-1.0.0{pyver_suffix}.egg-info/SOURCES.txt", b""
        )
        zip.writestr(
            f"{prefix}/Sampledist-1.0.0{pyver_suffix}.egg-info/top_level.txt", b""
        )
        zip.writestr(f"{prefix}/Sampledist-1.0.0{pyver_suffix}.egg-info/zip-safe", b"")
        zip.writestr("SCRIPTS/somecommand", b"#!python\nprint('hello')")

    return str(bdist_path)


@pytest.fixture
def egg_path(arch: str, pyver: str | None, tmp_path: Path) -> str:
    if pyver:
        filename = f"Sampledist-1.0.0-{pyver}-{arch}.egg"
    else:
        filename = "Sampledist-1.0.0.egg"

    bdist_path = tmp_path / filename
    with zipfile.ZipFile(bdist_path, "w") as zip:
        zip.writestr("sampledist/", b"")
        zip.writestr("EGG-INFO/", b"")
        zip.writestr("sampledist/__init__.py", b"")
        zip.writestr(f"sampledist/_extmodule.cp37-{arch}.pyd", b"")
        zip.writestr("EGG-INFO/dependency_links.txt", b"")
        zip.writestr("EGG-INFO/PKG-INFO", PKG_INFO.encode("utf-8"))
        zip.writestr("EGG-INFO/SOURCES.txt", b"")
        zip.writestr("EGG-INFO/top_level.txt", b"")
        zip.writestr("EGG-INFO/zip-safe", b"")

    return str(bdist_path)


def test_egg_re() -> None:
    """Make sure egg_info_re matches."""
    egg_names_path = os.path.join(os.path.dirname(__file__), "eggnames.txt")
    with open(egg_names_path, encoding="utf-8") as egg_names:
        for line in egg_names:
            line = line.strip()
            if line:
                assert egg_filename_re.match(line), line


def test_convert_egg_file(
    egg_path: str, tmp_path: Path, arch: str, expected_wheelfile: bytes
) -> None:
    convert([egg_path], str(tmp_path), verbose=False)
    wheel_path = next(path for path in tmp_path.iterdir() if path.suffix == ".whl")
    assert WHEEL_INFO_RE.match(wheel_path.name)
    with WheelFile(wheel_path) as wf:
        assert wf.read("sampledist-1.0.0.dist-info/METADATA") == EXPECTED_METADATA
        assert wf.read("sampledist-1.0.0.dist-info/WHEEL") == expected_wheelfile


def test_convert_egg_directory(
    egg_path: str,
    tmp_path: Path,
    tmp_path_factory: TempPathFactory,
    arch: str,
    expected_wheelfile: bytes,
) -> None:
    with zipfile.ZipFile(egg_path) as egg_file:
        egg_dir_path = tmp_path_factory.mktemp("eggdir") / Path(egg_path).name
        egg_dir_path.mkdir()
        egg_file.extractall(egg_dir_path)

    convert([str(egg_dir_path)], str(tmp_path), verbose=False)
    wheel_path = next(path for path in tmp_path.iterdir() if path.suffix == ".whl")
    assert WHEEL_INFO_RE.match(wheel_path.name)
    with WheelFile(wheel_path) as wf:
        assert wf.read("sampledist-1.0.0.dist-info/METADATA") == EXPECTED_METADATA
        assert wf.read("sampledist-1.0.0.dist-info/WHEEL") == expected_wheelfile


def test_convert_bdist_wininst(
    bdist_wininst_path: str,
    tmp_path: Path,
    arch: str,
    expected_wheelfile: bytes,
) -> None:
    convert([bdist_wininst_path], str(tmp_path), verbose=False)
    wheel_path = next(path for path in tmp_path.iterdir() if path.suffix == ".whl")
    assert WHEEL_INFO_RE.match(wheel_path.name)
    with WheelFile(wheel_path) as wf:
        assert (
            wf.read("sampledist-1.0.0.data/scripts/somecommand")
            == b"#!python\nprint('hello')"
        )
        assert wf.read("sampledist-1.0.0.dist-info/METADATA") == EXPECTED_METADATA
        assert wf.read("sampledist-1.0.0.dist-info/WHEEL") == expected_wheelfile
