"""
Wheel command-line utility.
"""

import os
import hashlib
import sys
import wheel.install
import wheel.signatures
import json
from glob import iglob
from ..util import urlsafe_b64decode, urlsafe_b64encode, native, binary
from ..wininst2wheel import bdist_wininst2wheel
from ..egg2wheel import egg2wheel

import argparse

def keygen():
    """Generate a public/private key pair."""
    import wheel.keys
    import keyring
    ed25519ll = wheel.signatures.get_ed25519ll()

    wk = wheel.keys.WheelKeys().load()
    
    keypair = ed25519ll.crypto_sign_keypair()
    vk = native(urlsafe_b64encode(keypair.vk))
    sk = native(urlsafe_b64encode(keypair.sk))
    kr = keyring.get_keyring()
    kr.set_password("wheel", vk, sk)
    sys.stdout.write("Created Ed25519 keypair with vk={0}\n".format(vk))
    if isinstance(kr, keyring.backend.BasicFileKeyring):
        sys.stdout.write("in {0}\n".format(kr.file_path))
    else:
        sys.stdout.write("in %r\n" % kr.__class__)

    sk2 = kr.get_password('wheel', vk)
    if sk2 != sk:
        raise Exception("Keyring is broken. Could not retrieve secret key.")
    
    sys.stdout.write("Trusting {0} to sign and verify all packages.\n".format(vk))
    wk.add_signer('+', vk)
    wk.trust('+', vk)
    wk.save()

def sign(wheelfile, replace=False):
    """Sign a wheel"""
    import wheel.keys
    import keyring
    ed25519ll = wheel.signatures.get_ed25519ll()
    
    wf = wheel.install.WheelFile(wheelfile, append=True)
    wk = wheel.keys.WheelKeys().load()
    
    name = wf.parsed_filename.group('name')
    sign_with = wk.signers(name)[0]
    sys.stdout.write("Signing {0} with {1}\n".format(name, sign_with[1]))
    
    vk = sign_with[1]
    kr = keyring.get_keyring()
    sk = kr.get_password('wheel', vk)
    keypair = ed25519ll.Keypair(urlsafe_b64decode(binary(vk)), 
                                urlsafe_b64decode(binary(sk)))
    
    
    record_name = wf.distinfo_name + '/RECORD'
    sig_name = wf.distinfo_name + '/RECORD.jws'
    if sig_name in wf.zipfile.namelist(): 
        raise NotImplementedError("Wheel is already signed")
    record_data = wf.zipfile.read(record_name)
    payload = {"hash":"sha256="+native(urlsafe_b64encode(hashlib.sha256(record_data).digest()))}
    sig = wheel.signatures.sign(payload, keypair)
    wf.zipfile.writestr(sig_name, json.dumps(sig, sort_keys=True))
    wf.zipfile.close()

def verify(wheelfile):
    """Verify a wheel."""
    import pprint
    wf = wheel.install.WheelFile(wheelfile)
    sig_name = wf.distinfo_name + '/RECORD.jws'
    sig = json.loads(native(wf.zipfile.open(sig_name).read()))
    sys.stdout.write("Signatures are internally consistent.\n%s\n" % (
                     pprint.pformat(wheel.signatures.verify(sig),)))

def unpack(wheelfile, dest='.'):
    """Unpack a wheel.

    Wheel content will be unpacked to {dest}/{name}-{ver}, where {name}
    is the package name and {ver} its version.

    :param wheelfile: The path to the wheel.
    :param dest: Destination directory (default to current directory).
    """
    wf = wheel.install.WheelFile(wheelfile)
    namever = wf.parsed_filename.group('namever')
    destination = os.path.join(dest, namever)
    sys.stdout.write("Unpacking to: %s\n" % (destination))
    wf.zipfile.extractall(destination)
    wf.zipfile.close()    

def install(wheelfile, force=False):
    """Install a wheel.
    
    :param wheelfile: The path to the wheel.
    """
    wf = wheel.install.WheelFile(wheelfile)
    if not force:
        if not wf.supports_current_python():
            msg = ("{} is not compatible with this Python. " 
                   "--force to install anyway.".format(wheelfile))
            raise Exception(msg)
    wf.install(force)
    wf.zipfile.close()

def convert(installers, dest_dir, verbose):
    for pat in installers:
        for installer in iglob(pat):
            if os.path.splitext(installer)[1] == '.egg':
                conv = egg2wheel
            else:
                conv = bdist_wininst2wheel
            if verbose:
                sys.stdout.write("{}... ".format(installer))
            conv(installer, dest_dir)
            if verbose:
                sys.stdout.write("OK\n")

def parser():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(help="commands")
    
    def keygen_f(args):
        keygen()
    keygen_parser = s.add_parser('keygen', help='Generate signing key')
    keygen_parser.add_argument('wheelfile', help='Wheel file') 
    keygen_parser.set_defaults(func=keygen_f)
    
    def sign_f(args):
        sign(args.wheelfile)    
    sign_parser = s.add_parser('sign', help='Sign wheel')
    sign_parser.add_argument('wheelfile', help='Wheel file')
    sign_parser.set_defaults(func=sign_f)
    
    def verify_f(args):
        verify(args.wheelfile)
    verify_parser = s.add_parser('verify', help='Verify signed wheel')
    verify_parser.add_argument('wheelfile', help='Wheel file')
    verify_parser.set_defaults(func=verify_f)
    
    def unpack_f(args):
        unpack(args.wheelfile, args.dest)
    unpack_parser = s.add_parser('unpack', help='Unpack wheel')
    unpack_parser.add_argument('--dest', '-d', help='Destination directory',
                               default='.')
    unpack_parser.add_argument('wheelfile', help='Wheel file')
    unpack_parser.set_defaults(func=unpack_f)
    
    def install_f(args):
        install(args.wheelfile, args.force)
    install_parser = s.add_parser('install', help='Install wheel')
    install_parser.add_argument('wheelfile', help='Wheel file')
    install_parser.add_argument('--force', '-f', default=False, 
                                action='store_true',
                                help='Install incompatible wheel files and '
                                'overwrite any files that are in the way.')
    install_parser.set_defaults(func=install_f)

    def convert_f(args):
        convert(args.installers, args.dest_dir, args.verbose)
    convert_parser = s.add_parser('convert', help='Convert egg or wininst to wheel')
    convert_parser.add_argument('installers', nargs='*', help='Installers to convert')
    convert_parser.add_argument('--dest-dir', '-d', default=os.path.curdir,
            help="Directory to store wheels (default %(default)s)")
    convert_parser.add_argument('--verbose', '-v', action='store_true')
    convert_parser.set_defaults(func=convert_f)
    
    return p

def main():
    p = parser()
    args = p.parse_args()
    args.func(args)
    
