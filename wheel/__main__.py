"""
Wheel command-line utility.
"""

import baker
import ed25519ll
import sys
import keyring
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
def sign():
    """Sign a wheel"""
    pass

def main():
    wb.run()
    
if __name__ == "__main__":
    wb.run()
