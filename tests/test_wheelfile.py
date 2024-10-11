from __future__ import annotations

import stat
import sys
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from wheel.cli import WheelError
from wheel.wheelfile import WheelFile


@pytest.fixture
def wheel_path(tmp_path):
    return str(tmp_path.joinpath("test-1.0-py2.py3-none-any.whl"))


@pytest.mark.parametrize(
    "filename",
    [
        "foo-2-py3-none-any.whl",
        "foo-2-py2.py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl",
    ],
)
def test_wheelfile_re(filename, tmp_path):
    # Regression test for #208 and #485
    path = tmp_path.joinpath(filename)
    with WheelFile(str(path), "w") as wf:
        assert wf.parsed_filename.group("namever") == "foo-2"


@pytest.mark.parametrize(
    "filename",
    [
        "test.whl",
        "test-1.0.whl",
        "test-1.0-py2.whl",
        "test-1.0-py2-none.whl",
        "test-1.0-py2-none-any",
        "test-1.0-py 2-none-any.whl",
    ],
)
def test_bad_wheel_filename(filename):
    exc = pytest.raises(WheelError, WheelFile, filename)
    exc.match(f"^Bad wheel filename {filename!r}$")


def test_missing_record(wheel_path):
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, w0rld!")\n')

    exc = pytest.raises(WheelError, WheelFile, wheel_path)
    exc.match("^Missing test-1.0.dist-info/RECORD file$")


def test_unsupported_hash_algorithm(wheel_path):
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, w0rld!")\n')
        zf.writestr(
            "test-1.0.dist-info/RECORD",
            "hello/héllö.py,sha000=bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo,25",
        )

    exc = pytest.raises(WheelError, WheelFile, wheel_path)
    exc.match("^Unsupported hash algorithm: sha000$")


@pytest.mark.parametrize(
    "algorithm, digest",
    [("md5", "4J-scNa2qvSgy07rS4at-Q"), ("sha1", "QjCnGu5Qucb6-vir1a6BVptvOA4")],
    ids=["md5", "sha1"],
)
def test_weak_hash_algorithm(wheel_path, algorithm, digest):
    hash_string = f"{algorithm}={digest}"
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, w0rld!")\n')
        zf.writestr("test-1.0.dist-info/RECORD", f"hello/héllö.py,{hash_string},25")

    exc = pytest.raises(WheelError, WheelFile, wheel_path)
    exc.match(rf"^Weak hash algorithm \({algorithm}\) is not permitted by PEP 427$")


@pytest.mark.parametrize(
    "algorithm, digest",
    [
        ("sha256", "bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo"),
        ("sha384", "cDXriAy_7i02kBeDkN0m2RIDz85w6pwuHkt2PZ4VmT2PQc1TZs8Ebvf6eKDFcD_S"),
        (
            "sha512",
            "kdX9CQlwNt4FfOpOKO_X0pn_v1opQuksE40SrWtMyP1NqooWVWpzCE3myZTfpy8g2azZON_"
            "iLNpWVxTwuDWqBQ",
        ),
    ],
    ids=["sha256", "sha384", "sha512"],
)
def test_testzip(wheel_path, algorithm, digest):
    hash_string = f"{algorithm}={digest}"
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, world!")\n')
        zf.writestr("test-1.0.dist-info/RECORD", f"hello/héllö.py,{hash_string},25")

    with WheelFile(wheel_path) as wf:
        wf.testzip()


def test_testzip_missing_hash(wheel_path):
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, world!")\n')
        zf.writestr("test-1.0.dist-info/RECORD", "")

    with WheelFile(wheel_path) as wf:
        exc = pytest.raises(WheelError, wf.testzip)
        exc.match("^No hash found for file 'hello/héllö.py'$")


def test_testzip_bad_hash(wheel_path):
    with ZipFile(wheel_path, "w") as zf:
        zf.writestr("hello/héllö.py", 'print("Héllö, w0rld!")\n')
        zf.writestr(
            "test-1.0.dist-info/RECORD",
            "hello/héllö.py,sha256=bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo,25",
        )

    with WheelFile(wheel_path) as wf:
        exc = pytest.raises(WheelError, wf.testzip)
        exc.match("^Hash mismatch for file 'hello/héllö.py'$")


def test_write_str(wheel_path):
    with WheelFile(wheel_path, "w") as wf:
        wf.writestr("hello/héllö.py", 'print("Héllö, world!")\n')
        wf.writestr("hello/h,ll,.py", 'print("Héllö, world!")\n')

    with ZipFile(wheel_path, "r") as zf:
        infolist = zf.infolist()
        assert len(infolist) == 3
        assert infolist[0].filename == "hello/héllö.py"
        assert infolist[0].file_size == 25
        assert infolist[1].filename == "hello/h,ll,.py"
        assert infolist[1].file_size == 25
        assert infolist[2].filename == "test-1.0.dist-info/RECORD"

        record = zf.read("test-1.0.dist-info/RECORD")
        assert record.decode("utf-8") == (
            "hello/héllö.py,sha256=bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo,25\n"
            '"hello/h,ll,.py",sha256=bv-QV3RciQC2v3zL8Uvhd_arp40J5A9xmyubN34OVwo,25\n'
            "test-1.0.dist-info/RECORD,,\n"
        )


def test_timestamp(tmp_path_factory, wheel_path, monkeypatch):
    # An environment variable can be used to influence the timestamp on
    # TarInfo objects inside the zip.  See issue #143.
    build_dir = tmp_path_factory.mktemp("build")
    for filename in ("one", "two", "three"):
        build_dir.joinpath(filename).write_text(filename + "\n", encoding="utf-8")

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
def test_attributes(tmp_path_factory, wheel_path):
    # With the change from ZipFile.write() to .writestr(), we need to manually
    # set member attributes.
    build_dir = tmp_path_factory.mktemp("build")
    files = (("foo", 0o644), ("bar", 0o755))
    for filename, mode in files:
        path = build_dir.joinpath(filename)
        path.write_text(filename + "\n", encoding="utf-8")
        path.chmod(mode)

    with WheelFile(wheel_path, "w") as wf:
        wf.write_files(str(build_dir))

    with ZipFile(wheel_path, "r") as zf:
        for filename, mode in files:
            info = zf.getinfo(filename)
            assert info.external_attr == (mode | stat.S_IFREG) << 16
            assert info.compress_type == ZIP_DEFLATED

        info = zf.getinfo("test-1.0.dist-info/RECORD")
        assert info.external_attr == (0o664 | stat.S_IFREG) << 16
