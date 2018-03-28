import hashlib
import zipfile
from io import BytesIO

import pytest

import wheel.archive
import wheel.install


def test_verifying_zipfile():
    if not hasattr(zipfile.ZipExtFile, '_update_crc'):
        pytest.skip('No ZIP verification. Missing ZipExtFile._update_crc.')

    bio = BytesIO()
    zf = zipfile.ZipFile(bio, 'w')
    zf.writestr("one", b"first file")
    zf.writestr("two", b"second file")
    zf.writestr("three", b"third file")
    zf.close()

    # In default mode, VerifyingZipFile checks the hash of any read file
    # mentioned with set_expected_hash(). Files not mentioned with
    # set_expected_hash() are not checked.
    vzf = wheel.install.VerifyingZipFile(bio, 'r')
    vzf.set_expected_hash("one", hashlib.sha256(b"first file").digest())
    vzf.set_expected_hash("three", "blurble")
    vzf.open("one").read()
    vzf.open("two").read()
    pytest.raises(wheel.install.BadWheelFile, vzf.open("three").read)

    # In strict mode, VerifyingZipFile requires every read file to be
    # mentioned with set_expected_hash().
    vzf.strict = True
    pytest.raises(wheel.install.BadWheelFile, vzf.open, "two")

    vzf.set_expected_hash("two", None)
    vzf.open("two").read()


def test_pop_zipfile():
    bio = BytesIO()
    zf = wheel.install.VerifyingZipFile(bio, 'w')
    zf.writestr("one", b"first file")
    zf.writestr("two", b"second file")
    zf.close()

    pytest.raises(RuntimeError, zf.pop)

    zf = wheel.install.VerifyingZipFile(bio, 'a')
    zf.pop()
    zf.close()

    zf = wheel.install.VerifyingZipFile(bio, 'r')
    assert len(zf.infolist()) == 1


def test_zipfile_timestamp(tmpdir, monkeypatch):
    # An environment variable can be used to influence the timestamp on
    # TarInfo objects inside the zip.  See issue #143.
    for filename in ('one', 'two', 'three'):
        tmpdir.join(filename).write(filename + '\n')

    # The earliest date representable in TarInfos, 1980-01-01
    monkeypatch.setenv('SOURCE_DATE_EPOCH', '315576060')

    zip_base_name = str(tmpdir.join('dummy'))
    zip_filename = wheel.archive.make_wheelfile_inner(zip_base_name, str(tmpdir))
    with zipfile.ZipFile(zip_filename, 'r', allowZip64=True) as zf:
        for info in zf.infolist():
            assert info.date_time[:3] == (1980, 1, 1)


def test_zipfile_attributes(tmpdir):
    # With the change from ZipFile.write() to .writestr(), we need to manually
    # set member attributes.
    files = (('foo', 0o644), ('bar', 0o755))
    for filename, mode in files:
        path = tmpdir.join(filename)
        path.write(filename + '\n')
        path.chmod(mode)

    zip_base_name = str(tmpdir.join('dummy'))
    zip_filename = wheel.archive.make_wheelfile_inner(zip_base_name, str(tmpdir))
    with zipfile.ZipFile(zip_filename, 'r', allowZip64=True) as zf:
        for filename, mode in files:
            info = zf.getinfo(str(tmpdir.join(filename)))
            assert info.external_attr == (mode | 0o100000) << 16
            assert info.compress_type == zipfile.ZIP_DEFLATED
