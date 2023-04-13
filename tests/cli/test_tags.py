from __future__ import annotations

import shutil
import sys
from pathlib import Path
from zipfile import ZipFile

import pytest

from wheel.cli import main, parser
from wheel.cli.tags import tags
from wheel.wheelfile import WheelFile

TESTDIR = Path(__file__).parent.parent
TESTWHEEL_NAME = "test-1.0-py2.py3-none-any.whl"
TESTWHEEL_PATH = TESTDIR / "testdata" / TESTWHEEL_NAME


@pytest.fixture
def wheelpath(tmp_path):
    wheels_dir = tmp_path / "wheels"
    wheels_dir.mkdir()
    fn = wheels_dir / TESTWHEEL_NAME
    # The str calls can be removed for Python 3.8+
    shutil.copy(str(TESTWHEEL_PATH), str(fn))
    return fn


def test_tags_no_args(wheelpath):
    newname = tags(str(wheelpath))
    assert TESTWHEEL_NAME == newname
    assert wheelpath.exists()


def test_python_tags(wheelpath):
    newname = tags(str(wheelpath), python_tags="py3")
    assert TESTWHEEL_NAME.replace("py2.py3", "py3") == newname
    output_file = wheelpath.parent / newname
    with WheelFile(str(output_file)) as f:
        output = f.read(f.dist_info_path + "/WHEEL")
    assert (
        output == b"Wheel-Version: 1.0\r\nGenerator: bdist_wheel (0.30.0)"
        b"\r\nRoot-Is-Purelib: false\r\nTag: py3-none-any\r\n"
    )
    output_file.unlink()

    newname = tags(str(wheelpath), python_tags="py2.py3")
    assert TESTWHEEL_NAME == newname

    newname = tags(str(wheelpath), python_tags="+py4", remove=True)
    assert not wheelpath.exists()
    assert TESTWHEEL_NAME.replace("py2.py3", "py2.py3.py4") == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_abi_tags(wheelpath):
    newname = tags(str(wheelpath), abi_tags="cp33m")
    assert TESTWHEEL_NAME.replace("none", "cp33m") == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()

    newname = tags(str(wheelpath), abi_tags="cp33m.abi3")
    assert TESTWHEEL_NAME.replace("none", "abi3.cp33m") == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()

    newname = tags(str(wheelpath), abi_tags="none")
    assert TESTWHEEL_NAME == newname

    newname = tags(str(wheelpath), abi_tags="+abi3.cp33m", remove=True)
    assert not wheelpath.exists()
    assert TESTWHEEL_NAME.replace("none", "abi3.cp33m.none") == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_plat_tags(wheelpath):
    newname = tags(str(wheelpath), platform_tags="linux_x86_64")
    assert TESTWHEEL_NAME.replace("any", "linux_x86_64") == newname
    output_file = wheelpath.parent / newname
    assert output_file.exists()
    output_file.unlink()

    newname = tags(str(wheelpath), platform_tags="linux_x86_64.win32")
    assert TESTWHEEL_NAME.replace("any", "linux_x86_64.win32") == newname
    output_file = wheelpath.parent / newname
    assert output_file.exists()
    output_file.unlink()

    newname = tags(str(wheelpath), platform_tags="+linux_x86_64.win32")
    assert TESTWHEEL_NAME.replace("any", "any.linux_x86_64.win32") == newname
    output_file = wheelpath.parent / newname
    assert output_file.exists()
    output_file.unlink()

    newname = tags(str(wheelpath), platform_tags="+linux_x86_64.win32")
    assert TESTWHEEL_NAME.replace("any", "any.linux_x86_64.win32") == newname
    output_file = wheelpath.parent / newname
    assert output_file.exists()

    newname2 = tags(str(output_file), platform_tags="-any")
    output_file.unlink()

    assert TESTWHEEL_NAME.replace("any", "linux_x86_64.win32") == newname2
    output_file2 = wheelpath.parent / newname2
    assert output_file2.exists()
    output_file2.unlink()

    newname = tags(str(wheelpath), platform_tags="any")
    assert TESTWHEEL_NAME == newname


def test_build_tag(wheelpath):
    newname = tags(str(wheelpath), build_tag="1bah")
    assert TESTWHEEL_NAME.replace("-py2", "-1bah-py2") == newname
    output_file = wheelpath.parent / newname
    assert output_file.exists()
    output_file.unlink()


@pytest.mark.parametrize(
    "build_tag, error",
    [
        pytest.param("foo", "build tag must begin with a digit", id="digitstart"),
        pytest.param("1-f", "invalid character ('-') in build tag", id="hyphen"),
    ],
)
def test_invalid_build_tag(wheelpath, build_tag, error, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", [sys.argv[0], "tags", "--build", build_tag])
    with pytest.raises(SystemExit) as exc:
        main()

    _, err = capsys.readouterr()
    assert exc.value.args[0] == 2
    assert f"error: argument --build: {error}" in err


def test_multi_tags(wheelpath):
    newname = tags(
        str(wheelpath),
        platform_tags="linux_x86_64",
        python_tags="+py4",
        build_tag="1",
    )
    assert "test-1.0-1-py2.py3.py4-none-linux_x86_64.whl" == newname

    output_file = wheelpath.parent / newname
    assert output_file.exists()
    with WheelFile(str(output_file)) as f:
        output = f.read(f.dist_info_path + "/WHEEL")
    assert (
        output
        == b"Wheel-Version: 1.0\r\nGenerator: bdist_wheel (0.30.0)\r\nRoot-Is-Purelib:"
        b" false\r\nTag: py2-none-linux_x86_64\r\nTag: py3-none-linux_x86_64\r\nTag:"
        b" py4-none-linux_x86_64\r\nBuild: 1\r\n"
    )
    output_file.unlink()


def test_tags_command(capsys, wheelpath):
    args = [
        "tags",
        "--python-tag",
        "py3",
        "--abi-tag",
        "cp33m",
        "--platform-tag",
        "linux_x86_64",
        "--build",
        "7",
        str(wheelpath),
    ]
    p = parser()
    args = p.parse_args(args)
    args.func(args)
    assert wheelpath.exists()

    newname = capsys.readouterr().out.strip()
    assert "test-1.0-7-py3-cp33m-linux_x86_64.whl" == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_tags_command_del(capsys, wheelpath):
    args = [
        "tags",
        "--python-tag",
        "+py4",
        "--abi-tag",
        "cp33m",
        "--platform-tag",
        "linux_x86_64",
        "--remove",
        str(wheelpath),
    ]
    p = parser()
    args = p.parse_args(args)
    args.func(args)
    assert not wheelpath.exists()

    newname = capsys.readouterr().out.strip()
    assert "test-1.0-py2.py3.py4-cp33m-linux_x86_64.whl" == newname
    output_file = wheelpath.parent / newname
    output_file.unlink()


def test_permission_bits(capsys, wheelpath):
    args = [
        "tags",
        "--python-tag=+py4",
        str(wheelpath),
    ]
    p = parser()
    args = p.parse_args(args)
    args.func(args)

    newname = capsys.readouterr().out.strip()
    assert "test-1.0-py2.py3.py4-none-any.whl" == newname
    output_file = wheelpath.parent / newname

    with ZipFile(str(output_file), "r") as outf:
        with ZipFile(str(wheelpath), "r") as inf:
            for member in inf.namelist():
                if not member.endswith("/RECORD"):
                    out_attr = outf.getinfo(member).external_attr
                    inf_attr = inf.getinfo(member).external_attr
                    assert (
                        out_attr == inf_attr
                    ), f"{member} 0x{out_attr:012o} != 0x{inf_attr:012o}"

    output_file.unlink()
