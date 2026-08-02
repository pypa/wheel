from __future__ import annotations

import shutil
import struct
import zipfile
from pathlib import Path
from subprocess import CalledProcessError
from zipfile import ZIP_STORED, ZipFile, ZipInfo

import pytest

from wheel._commands.tags import tags
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


def test_retag_does_not_leak_zip64_into_local_headers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A ZIP64 extra field (id 0x0001) stores the central-directory-only
    # header offset; it is invalid in a local file header. Retagging copied
    # each source ZipInfo verbatim, so ZIP64 entries produced corrupt local
    # headers that strict parsers reject (#692). Force ZIP64 on small files.
    monkeypatch.setattr(zipfile, "ZIP64_LIMIT", 512)

    # A non-ZIP64 extra field whose payload embeds the ZIP64 header id, to
    # confirm the fix walks the extra-field structure rather than blindly
    # stripping the 0x0001 byte pattern wherever it appears.
    custom_extra = b"\xca\xfe\x05\x00\x01\x00\x99\x99\x99"
    init_info = ZipInfo("test/__init__.py")
    init_info.extra = custom_extra

    wheelpath = tmp_path / "test-1.0-py3-none-any.whl"
    with WheelFile(wheelpath, "w", compression=ZIP_STORED) as wheel_file:
        wheel_file.writestr("test/padding1", b"x" * 400)
        wheel_file.writestr("test/padding2", b"x" * 400)
        wheel_file.writestr(init_info, b"")
        wheel_file.writestr(
            "test-1.0.dist-info/WHEEL",
            "Wheel-Version: 1.0\nRoot-Is-Purelib: true\nTag: py3-none-any\n",
        )
        wheel_file.writestr(
            "test-1.0.dist-info/METADATA",
            "Metadata-Version: 2.1\nName: test\nVersion: 1.0\n",
        )

    # Sanity check: the source really has ZIP64 entries.
    with ZipFile(wheelpath) as source:
        assert any(item.extra[:2] == b"\x01\x00" for item in source.infolist())

    newname = tags(str(wheelpath), platform_tags="linux_x86_64")
    output_file = wheelpath.parent / newname

    with ZipFile(output_file) as retagged, output_file.open("rb") as raw:
        for item in retagged.infolist():
            raw.seek(item.header_offset + 26)
            name_size, extra_size = struct.unpack("<HH", raw.read(4))
            raw.seek(name_size, 1)
            extra = raw.read(extra_size)
            assert extra[:2] != b"\x01\x00", (
                f"{item.filename} local header carries a ZIP64 extra field"
            )
            if item.filename == "test/__init__.py":
                assert extra == custom_extra, (
                    "non-ZIP64 extra field was not preserved on retag"
                )

    output_file.unlink()
