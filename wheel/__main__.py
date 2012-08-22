"""
Wheel command-line utility.
"""

import baker
import ed25519ll
import sys
import keyring
import wheel.install
import wheel.signatures
import json
from .util import urlsafe_b64decode, urlsafe_b64encode

wb = baker.Baker()

@wb.command()
def keygen():
    """Generate a public/private key pair."""
    keypair = ed25519ll.crypto_sign_keypair()
    vk = urlsafe_b64encode(keypair.vk).decode('latin1')
    sk = urlsafe_b64encode(keypair.sk).decode('latin1')
    kr = keyring.get_keyring()
    kr.set_password("wheel", vk, sk)
    sys.stdout.write("Created Ed25519 keypair with vk={0}\n".format(vk))
    if isinstance(kr, keyring.backend.BasicFileKeyring):
        sys.stdout.write("in {0}\n".format(kr.file_path))
    else:
        sys.stdout.write("in %r\n" % kr)

    sk2 = kr.get_password('wheel', vk)
    if sk2 != sk:
        raise Exception("Keyring is broken. Could not retrieve secret key.")

@wb.command()
def sign(wheelfile, replace=False):
    """Sign a wheel"""
    import hashlib    
    wf = wheel.install.WheelFile(wheelfile, append=True)
    record_name = wf.distinfo_name + '/RECORD'
    sig_name = wf.distinfo_name + '/RECORD.jws'
    if sig_name in wf.zipfile.namelist(): 
        raise NotImplementedError("Wheel is already signed")
    record_data = wf.zipfile.read(record_name)
    payload = {"hash":"sha256=%s" % urlsafe_b64encode(hashlib.sha256(record_data).digest())}
    sig = wheel.signatures.sign(payload, ed25519ll.crypto_sign_keypair())
    wf.zipfile.writestr(sig_name, json.dumps(sig, sort_keys=True))
    wf.zipfile.close()

@wb.command()
def verify(wheelfile):
    """Verify a wheel."""
    import pprint
    wf = wheel.install.WheelFile(wheelfile)
    sig_name = wf.distinfo_name + '/RECORD.jws'
    sig = json.loads(wf.zipfile.open(sig_name).read())
    sys.stdout.write("Signatures are internally consistent.\n%s\n" % (
                     pprint.pformat(wheel.signatures.verify(sig),)))

def main():
    wb.run()
    
if __name__ == "__main__":
    wb.run()
