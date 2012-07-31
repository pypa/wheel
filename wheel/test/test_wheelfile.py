import wheel.install
import hashlib
try:
    from StringIO import StringIO
except ImportError:
    from io import BytesIO as StringIO
import zipfile

def test_verifying_zipfile():
    sio = StringIO()
    zf = zipfile.ZipFile(sio, 'w')
    zf.writestr("one", b"first file")
    zf.writestr("two", b"second file")
    zf.writestr("three", b"third file")
    zf.close()
    
    vzf = wheel.install.VerifyingZipFile(sio, 'r')
    vzf.set_expected_hash("one", hashlib.sha256(b"first file").digest())
    vzf.set_expected_hash("three", "blurble")
    vzf.open("one").read()
    vzf.open("two").read()
    try:
        vzf.open("three").read()
    except wheel.install.BadWheelFile:
        pass
    else:
        raise Exception("expected exception 'BadWheelFile()'")
    