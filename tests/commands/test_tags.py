from __future__ import annotations

import shutil
from pathlib import Path
from subprocess import CalledProcessError
from zipfile import ZipFile

import pytest

from wheel.wheelfile import WheelFile

from .util import run_command

TESTWHEEL_NAME = "test-1.0-py2.py3-none-any.whl"
TESTWHEEL_PATH = Path(__file__).parent.parent / "testdata" / TESTWHEEL_NAME


@pytest.fixture
def wheelpath(tmp_path: Path) -> Path:
    wheels_dir = tmp_path / "wheels"
    wheels_dir.mkdir()
    fn = wheels_dir / TESTWHEEL_NAME
    shutil.copy(TESTWHEEL_PATH, fn)
    return fn


def test_tags_no_args(wheelpath: Path) -> None:
    newname = run_command("tags", wheelpath).strip()
    assert newname == TESTWHEEL_NAME
    assert wheelpath.exists()


def test_python_tags(wheelpath: Path) -> None:
    newname = run_command("tags", "--python-tag", "py3", wheelpath).strip()
    assert newname == TESTWHEEL_NAME.replace("py2.py3", "py3")
    output_file = wheelpath.parent / newname
    with WheelFile(output_file) as f:
        output = f.read(f.dist_info_path + "/WHEEL")

    assert (
        output == b"Wheel-Version: 1.0\nGenerator: bdist_wheel (0.30.0)"
        b"\nRoot-Is-Purelib: false\nTag: py3-none-any\n\n"
    )
    output_file.unlink()

    newname = run_command("tags", wheelpath, "--python-tag", "py2.py3").strip()
    assert newname == TESTWHEEL_NAME

    newname = run_command("tags", "--remove", "--python-tag", "+py4", wheelpath).strip()
    assert not wheelpath.exists()
    assert newname == TESTWHEEL_NAME.replace("py2.py3", "py2.py3.py4")
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_abi_tags(wheelpath: Path) -> None:
    newname = run_command("tags", wheelpath, "--abi-tag", "cp33m").strip()
    assert newname == TESTWHEEL_NAME.replace("none", "cp33m")
    output_file = wheelpath.parent / newname
    output_file.unlink()

    newname = run_command("tags", wheelpath, "--abi-tag", "cp33m.abi3").strip()
    assert newname == TESTWHEEL_NAME.replace("none", "abi3.cp33m")
    output_file = wheelpath.parent / newname
    output_file.unlink()

    newname = run_command("tags", wheelpath, "--abi-tag", "none").strip()
    assert newname == TESTWHEEL_NAME

    newname = run_command(
        "tags", wheelpath, "--remove", "--abi-tag", "+abi3.cp33m"
    ).strip()
    assert not wheelpath.exists()
    assert newname == TESTWHEEL_NAME.replace("none", "abi3.cp33m.none")
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_plat_tags(wheelpath: Path) -> None:
    newname = run_command("tags", "--platform-tag", "linux_x86_64", wheelpath).strip()
    assert newname == TESTWHEEL_NAME.replace("any", "linux_x86_64")
    output_file = wheelpath.parent / newname
    assert output_file.exists()
    output_file.unlink()

    newname = run_command(
        "tags", "--platform-tag", "linux_x86_64.win32", wheelpath
    ).strip()
    assert newname == TESTWHEEL_NAME.replace("any", "linux_x86_64.win32")
    output_file = wheelpath.parent / newname
    assert output_file.exists()
    output_file.unlink()

    newname = run_command(
        "tags", "--platform-tag", "+linux_x86_64.win32", wheelpath
    ).strip()
    assert newname == TESTWHEEL_NAME.replace("any", "any.linux_x86_64.win32")
    output_file = wheelpath.parent / newname
    assert output_file.exists()
    output_file.unlink()

    newname = run_command(
        "tags", "--platform-tag", "+linux_x86_64.win32", wheelpath
    ).strip()
    assert newname == TESTWHEEL_NAME.replace("any", "any.linux_x86_64.win32")
    output_file = wheelpath.parent / newname
    assert output_file.exists()

    newname2 = run_command("tags", "--platform-tag=-any", output_file).strip()
    output_file.unlink()

    assert newname2 == TESTWHEEL_NAME.replace("any", "linux_x86_64.win32")
    output_file2 = wheelpath.parent / newname2
    assert output_file2.exists()
    output_file2.unlink()

    newname = run_command("tags", "--platform-tag", "any", wheelpath).strip()
    assert newname == TESTWHEEL_NAME


def test_build_tag(wheelpath: Path) -> None:
    newname = run_command("tags", "--build", "1bah", wheelpath).strip()
    assert newname == TESTWHEEL_NAME.replace("-py2", "-1bah-py2")
    output_file = wheelpath.parent / newname
    assert output_file.exists()

    newname = run_command("tags", "--build", "", wheelpath).strip()
    assert newname == TESTWHEEL_NAME
    output_file.unlink()


@pytest.mark.parametrize(
    "build_tag, error",
    [
        pytest.param("foo", "build tag must begin with a digit", id="digitstart"),
        pytest.param("1-f", "invalid character ('-') in build tag", id="hyphen"),
    ],
)
def test_invalid_build_tag(wheelpath: Path, build_tag: str, error: str) -> None:
    with pytest.raises(CalledProcessError) as exc_info:
        run_command("tags", "--build", build_tag, wheelpath, catch_systemexit=False)

    exc = exc_info.value
    assert exc.returncode == 2
    assert f"error: argument --build: {error}" in exc.stderr


def test_multi_tags(wheelpath: Path) -> None:
    newname = run_command(
        "tags",
        "--platform-tag",
        "linux_x86_64",
        "--python-tag",
        "+py4",
        "--build",
        "1",
        wheelpath,
    ).strip()
    assert newname == "test-1.0-1-py2.py3.py4-none-linux_x86_64.whl"

    output_file = wheelpath.parent / newname
    assert output_file.exists()
    with WheelFile(output_file) as f:
        output = f.read(f.dist_info_path + "/WHEEL")

    assert output == (
        b"Wheel-Version: 1.0\n"
        b"Generator: bdist_wheel (0.30.0)\nRoot-Is-Purelib: false\n"
        b"Tag: py2-none-linux_x86_64\n"
        b"Tag: py3-none-linux_x86_64\n"
        b"Tag: py4-none-linux_x86_64\n"
        b"Build: 1\n\n"
    )
    output_file.unlink()


def test_tags_command(wheelpath: Path) -> None:
    newname = run_command(
        "tags",
        "--python-tag",
        "py3",
        "--abi-tag",
        "cp33m",
        "--platform-tag",
        "linux_x86_64",
        "--build",
        "7",
        wheelpath,
    ).strip()
    assert "test-1.0-7-py3-cp33m-linux_x86_64.whl" == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_tags_command_del(wheelpath: Path) -> None:
    newname = run_command(
        "tags",
        "--python-tag",
        "+py4",
        "--abi-tag",
        "cp33m",
        "--platform-tag",
        "linux_x86_64",
        "--remove",
        wheelpath,
    ).strip()
    assert "test-1.0-py2.py3.py4-cp33m-linux_x86_64.whl" == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_permission_bits(wheelpath: Path) -> None:
    newname = run_command("tags", "--python-tag", "+py4", wheelpath).strip()
    assert "test-1.0-py2.py3.py4-none-any.whl" == newname
    output_file = wheelpath.parent / newname

    with ZipFile(output_file, "r") as outf, ZipFile(wheelpath, "r") as inf:
        for member in inf.namelist():
            member_info = inf.getinfo(member)
            if member_info.is_dir():
                continue

            if member_info.filename.endswith("/RECORD"):
                continue

            out_attr = outf.getinfo(member).external_attr
            inf_attr = member_info.external_attr
            assert out_attr == inf_attr, (
                f"{member} 0x{out_attr:012o} != 0x{inf_attr:012o}"
            )

    output_file.unlink()
