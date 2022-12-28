from __future__ import annotations

import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from pytest import MonkeyPatch, TempPathFactory

from wheel import WheelError
from wheel.wheelfile import WheelFile


@pytest.fixture
def wheel_path(tmp_path: Path) -> Path:
    return tmp_path / "test-1.0-py2.py3-none-any.whl"


@pytest.mark.parametrize(
    "filename",
    [
        "foo-2-py3-none-any.whl",
        "foo-2-py2.py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
    ],
)
def test_wheelfile_re(filename: str, tmp_path: Path) -> None:
    # Regression test for #208 and #485
    path = tmp_path / filename
    with WheelFile(path, "w") as wf:
        assert wf.parsed_filename.group("namever") == "foo-2"


def test_missing_record(wheel_path: Path) -> None:
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, w0rld!")\n')

    with pytest.raises(
        WheelError,
        match=(
            "^Cannot find a valid .dist-info directory. Is this really a wheel file\\?$"
        ),
    ):
        with WheelFile(wheel_path):
            pass


def test_unsupported_hash_algorithm(wheel_path: Path) -> None:
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, w0rld!")\n')
        zf.writestr(
            "test-1.0.dist-info/RECORD",
            "hello/héllö.py,sha000=bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo,25",
        )

    with pytest.raises(WheelError, match="^Unsupported hash algorithm: sha000$"):
        with WheelFile(wheel_path):
            pass


@pytest.mark.parametrize(
    "algorithm, digest",
    [
        pytest.param("md5", "4J-scNa2qvSgy07rS4at-Q", id="md5"),
        pytest.param("sha1", "QjCnGu5Qucb6-vir1a6BVptvOA4", id="sha1"),
    ],
)
def test_weak_hash_algorithm(wheel_path: Path, algorithm: str, digest: str) -> None:
    hash_string = f"{algorithm}={digest}"
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, w0rld!")\n')
        zf.writestr("test-1.0.dist-info/RECORD", f"hello/héllö.py,{hash_string},25")

    with pytest.raises(
        WheelError,
        match=rf"^Weak hash algorithm \({algorithm}\) is not permitted by PEP 427$",
    ):
        with WheelFile(wheel_path):
            pass


def test_write_str(wheel_path: Path) -> None:
    with WheelFile(wheel_path, "w") as wf:
        wf.writestr("hello/héllö.py", 'print("Héllö, world!")\n')
        wf.writestr("hello/h,ll,.py", 'print("Héllö, world!")\n')

    with ZipFile(wheel_path, "r") as zf:
        infolist = zf.infolist()
        assert len(infolist) == 4
        assert infolist[0].filename == "hello/héllö.py"
        assert infolist[0].file_size == 25
        assert infolist[1].filename == "hello/h,ll,.py"
        assert infolist[1].file_size == 25
        assert infolist[2].filename == "test-1.0.dist-info/WHEEL"
        assert infolist[3].filename == "test-1.0.dist-info/RECORD"

        record = zf.read("test-1.0.dist-info/RECORD")
        assert record.decode("utf-8") == (
            "hello/héllö.py,sha256=bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo,25\n"
            '"hello/h,ll,.py",sha256=bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo,25\n'
            "test-1.0.dist-info/WHEEL,"
            "sha256=xn45MTtJwj1QxDHLE3DKYDjLqYLb8DHEh5F6k8vFf5o,105\n"
            "test-1.0.dist-info/RECORD,,\n"
        )


def test_timestamp(
    tmp_path_factory: TempPathFactory, wheel_path: Path, monkeypatch: MonkeyPatch
) -> None:
    # An environment variable can be used to influence the timestamp on
    # TarInfo objects inside the zip.  See issue #143.
    build_dir = tmp_path_factory.mktemp("build")
    for filename in ("one", "two", "three"):
        build_dir.joinpath(filename).write_text(filename + "\n")

    # The earliest date representable in TarInfos, 1980-01-01
    monkeypatch.setenv("SOURCE_DATE_EPOCH", "315576060")

    with WheelFile(wheel_path, "w") as wf:
        wf.write_files(str(build_dir))

    with ZipFile(wheel_path, "r") as zf:
        for info in zf.infolist():
            assert info.date_time[:3] == (1980, 1, 1)
            assert info.compress_type == ZIP_DEFLATED


@pytest.mark.skipif(
    sys.platform == "win32", reason="Windows does not support UNIX-like permissions"
)
def test_attributes(tmp_path_factory: TempPathFactory, wheel_path: Path) -> None:
    # With the change from ZipFile.write() to .writestr(), we need to manually
    # set member attributes.
    build_dir = tmp_path_factory.mktemp("build")
    files = (("foo", 0o644), ("bar", 0o755))
    for filename, mode in files:
        path = build_dir / filename
        path.write_text(filename + "\n")
        path.chmod(mode)

    with WheelFile(wheel_path, "w") as wf:
        wf.write_files(str(build_dir))

    with ZipFile(wheel_path, "r") as zf:
        for filename, mode in files:
            info = zf.getinfo(filename)
            assert info.external_attr == (mode | 0o100000) << 16
            assert info.compress_type == ZIP_DEFLATED

        info = zf.getinfo("test-1.0.dist-info/RECORD")
        permissions = (info.external_attr >> 16) & 0o777
        assert permissions == 0o664
