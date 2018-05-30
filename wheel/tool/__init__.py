"""
Wheel command-line utility.
"""

from __future__ import print_function

import argparse
import os
import sys
from glob import iglob

from ..install import WheelFile


def require_pkgresources(name):
    try:
        import pkg_resources  # noqa: F401
    except ImportError:
        raise RuntimeError("'{0}' needs pkg_resources (part of setuptools).".format(name))


class WheelError(Exception):
    pass


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
    print("Unpacking to: %s" % (destination), file=sys.stderr)
    wf.zipfile.extractall(destination)
    wf.zipfile.close()


def convert(installers, dest_dir, verbose):
    require_pkgresources('wheel convert')

    # Only support wheel convert if pkg_resources is present
    from ..wininst2wheel import bdist_wininst2wheel
    from ..egg2wheel import egg2wheel

    for pat in installers:
        for installer in iglob(pat):
            if os.path.splitext(installer)[1] == '.egg':
                conv = egg2wheel
            else:
                conv = bdist_wininst2wheel
            if verbose:
                print("{}... ".format(installer))
                sys.stdout.flush()
            conv(installer, dest_dir)
            if verbose:
                print("OK")


def parser():
    p = argparse.ArgumentParser()
    s = p.add_subparsers(help="commands")

    def unpack_f(args):
        unpack(args.wheelfile, args.dest)
    unpack_parser = s.add_parser('unpack', help='Unpack wheel')
    unpack_parser.add_argument('--dest', '-d', help='Destination directory',
                               default='.')
    unpack_parser.add_argument('wheelfile', help='Wheel file')
    unpack_parser.set_defaults(func=unpack_f)

    def convert_f(args):
        convert(args.installers, args.dest_dir, args.verbose)
    convert_parser = s.add_parser('convert', help='Convert egg or wininst to wheel')
    convert_parser.add_argument('installers', nargs='*', help='Installers to convert')
    convert_parser.add_argument('--dest-dir', '-d', default=os.path.curdir,
                                help="Directory to store wheels (default %(default)s)")
    convert_parser.add_argument('--verbose', '-v', action='store_true')
    convert_parser.set_defaults(func=convert_f)

    def version_f(args):
        from .. import __version__
        print("wheel %s" % __version__)
    version_parser = s.add_parser('version', help='Print version and exit')
    version_parser.set_defaults(func=version_f)

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
        try:
            args.func(args)
            return 0
        except WheelError as e:
            print(e, file=sys.stderr)

    return 1
