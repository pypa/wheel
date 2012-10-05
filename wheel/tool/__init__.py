"""
Wheel command-line utility.
"""

import os
import hashlib
import sys
import json
from glob import iglob
from pkg_resources import Distribution, Requirement
from .. import signatures
from ..util import urlsafe_b64decode, urlsafe_b64encode, native, binary
from ..wininst2wheel import bdist_wininst2wheel
from ..egg2wheel import egg2wheel
from ..install import WheelFile

import argparse

# For testability
def get_keyring():    
    try:
        from ..signatures import keys
        import keyring
    except ImportError:
        raise Exception("Install wheel[signatures] (keyring, dirspec) for signatures")
    return keys.WheelKeys, keyring

def keygen(get_keyring=get_keyring):
    """Generate a public/private key pair."""
    WheelKeys, keyring = get_keyring()
    
    ed25519ll = signatures.get_ed25519ll()

    wk = WheelKeys().load()
    
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

def sign(wheelfile, replace=False, get_keyring=get_keyring):
    """Sign a wheel"""
    WheelKeys, keyring = get_keyring()

    ed25519ll = signatures.get_ed25519ll()
    
    wf = WheelFile(wheelfile, append=True)
    wk = WheelKeys().load()
    
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
    sig = signatures.sign(payload, keypair)
    wf.zipfile.writestr(sig_name, json.dumps(sig, sort_keys=True))
    wf.zipfile.close()

def verify(wheelfile):
    """Verify a wheel."""
    import pprint
    wf = install.WheelFile(wheelfile)
    sig_name = wf.distinfo_name + '/RECORD.jws'
    sig = json.loads(native(wf.zipfile.open(sig_name).read()))
    sys.stdout.write("Signatures are internally consistent.\n%s\n" % (
                     pprint.pformat(signatures.verify(sig),)))

def unpack(wheelfile, dest='.'):
    """Unpack a wheel.

    Wheel content will be unpacked to {dest}/{name}-{ver}, where {name}
    is the package name and {ver} its version.

    :param wheelfile: The path to the wheel.
    :param dest: Destination directory (default to current directory).
    """
    wf = WheelFile(wheelfile)
    namever = wf.parsed_filename.group('namever')
    destination = os.path.join(dest, namever)
    sys.stdout.write("Unpacking to: %s\n" % (destination))
    wf.zipfile.extractall(destination)
    wf.zipfile.close()    

def matches_requirement(req, wheels):
    """List of wheels matching a requirement.

    :param req: The requirement to satisfy
    :param wheels: List of wheels to search.
    """
    selected =  []
    for wf in wheels:
        f = wf.parsed_filename
        dist = Distribution(project_name=f.group("name"), version=f.group("ver"))
        if dist in req:
            selected.append(wf)
    return selected

def install(requirements, requirements_file=None,
            wheel_dirs=None, force=False, list_files=False):
    """Install wheels.
    
    :param requirements: A list of requirements or wheel files to install.
    :param requirements_file: A file containint requirements to install.
    :param wheel_dirs: A list of directories to search for wheels.
    :param force: Install a wheel file even if it is not compatible.
    :param list_files: Only list the files to install, don't install them.
    """

    # If no wheel directories specified, use the WHEELPATH environment
    # variable, or the current directory if that is not set.
    if not wheel_dirs:
        wheelpath = os.getenv("WHEELPATH")
        if wheelpath:
            wheel_dirs = wheelpath.split(os.pathsep)
        else:
            wheel_dirs = [ os.path.curdir ]

    # Get a list of all valid wheels in wheel_dirs
    all_wheels = []
    for d in wheel_dirs:
        for w in os.listdir(d):
            if w.endswith('.whl'):
                wf = WheelFile(os.path.join(d, w))
                if wf.supported:
                    all_wheels.append(wf)

    # If there is a requirements file, add it to the list of requirements
    if requirements_file:
        # If the file doesn't exist, search for it in wheel_dirs
        # This allows standard requirements files to be stored with the
        # wheels.
        if not os.path.exists(requirements_file):
            for d in wheel_dirs:
                name = os.path.join(d, requirements_file)
                if os.path.exists(name):
                    requirements_file = name
                    break

        with open(requirements_file) as fd:
            requirements.extend(fd)

    to_install = []
    for req in requirements:
        if req.endswith('.whl'):
            # Explicitly specified wheel filename
            if os.path.exists(req):
                wf = WheelFile(req)
                if wf.supported or force:
                    to_install.append(wf)
                else:
                    msg = ("{} is not compatible with this Python. "
                           "--force to install anyway.".format(req))
                    raise Exception(msg)
            else:
                # We could search on wheel_dirs, but it's probably OK to
                # assume the user has made an error.
                raise Exception("No such wheel file: {}".format(req))
            continue

        # We have a requirement spec
        req = Requirement.parse(req)
        matches = matches_requirement(req, all_wheels)
        if not matches:
            raise Exception("No match for requirement {}".format(req))
        to_install.append(max(matches))

    # We now have a list of wheels to install
    if list_files:
        sys.stdout.write("Installing:\n")
    for wf in to_install:
        if list_files:
            sys.stdout.write("    {}\n".format(wf.filename))
            continue
        wf.install(force=force)
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
                sys.stdout.flush()
            conv(installer, dest_dir)
            if verbose:
                sys.stdout.write("OK\n")

def parser():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(help="commands")
    
    def keygen_f(args):
        keygen()
    keygen_parser = s.add_parser('keygen', help='Generate signing key')
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
        install(args.requirements, args.requirements_file,
                args.wheel_dirs, args.force, args.list_files)
    install_parser = s.add_parser('install', help='Install wheels')
    install_parser.add_argument('requirements', nargs='*',
                                help='Requirements to install.')
    install_parser.add_argument('--force', default=False,
                                action='store_true',
                                help='Install incompatible wheel files.')
    install_parser.add_argument('--wheel-dir', '-d', action='append',
                                dest='wheel_dirs',
                                help='Directories containing wheels.')
    install_parser.add_argument('--requirements-file', '-r', 
                                help="A file containing requirements to "
                                "install.")
    install_parser.add_argument('--list', '-l', default=False,
                                dest='list_files',
                                action='store_true',
                                help="List wheels which would be installed, "
                                "but don't actually install anything.")
    install_parser.set_defaults(func=install_f)

    def convert_f(args):
        convert(args.installers, args.dest_dir, args.verbose)
    convert_parser = s.add_parser('convert', help='Convert egg or wininst to wheel')
    convert_parser.add_argument('installers', nargs='*', help='Installers to convert')
    convert_parser.add_argument('--dest-dir', '-d', default=os.path.curdir,
            help="Directory to store wheels (default %(default)s)")
    convert_parser.add_argument('--verbose', '-v', action='store_true')
    convert_parser.set_defaults(func=convert_f)
    
    def help_f(args):
        p.print_help()
    help_parser = s.add_parser('help', help='Show this help')
    help_parser.set_defaults(func=help_f)

    return p

def main():
    p = parser()
    args = p.parse_args()
    if not hasattr(args, 'func'):
        p.print_help()
    else:
        # XXX on Python 3.3 we get 'args has no func' rather than short help.
        args.func(args)
