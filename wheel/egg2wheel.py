#!/usr/bin/env python
import os.path
import re
import sys
import tempfile
import zipfile
import wheel.bdist_wheel
import distutils.dist
from distutils.archive_util import make_archive
from shutil import rmtree
from argparse import ArgumentParser
from glob import iglob

egg_info_re = re.compile(r'''(?P<name>.+?)-(?P<ver>.+?)
    (-(?P<pyver>.+?))?(-(?P<arch>.+?))?.egg''', re.VERBOSE)

def egg2wheel(egg_path, dest_dir):
    egg_info = egg_info_re.match(os.path.basename(egg_path)).groupdict()
    egg = zipfile.ZipFile(egg_path)
    dir = tempfile.mkdtemp(suffix="_e2w")
    egg.extractall(dir)
    dist_info = "%s-%s" % (egg_info['name'], egg_info['ver'])
    abi = 'none'
    pyver = egg_info['pyver'].replace('.', '')
    arch = (egg_info['arch'] or 'any').replace('.', '_').replace('-', '_')
    if arch != 'any':
        # assume all binary eggs are for CPython
        pyver = 'cp' + pyver[2:]
    wheel_name = '-'.join((
                          dist_info,
                          pyver,
                          abi,
                          arch
                          ))
    bw = wheel.bdist_wheel.bdist_wheel(distutils.dist.Distribution())
    bw.root_is_purelib = egg_info['arch'] is None
    dist_info_dir = os.path.join(dir, '%s.dist-info' % dist_info)
    bw.egg2dist(os.path.join(dir, 'EGG-INFO'),
                dist_info_dir)
    bw.write_wheelfile(dist_info_dir, generator='egg2wheel')
    bw.write_record(dir, dist_info_dir)
    filename = make_archive(os.path.join(dest_dir, wheel_name), 'zip', root_dir=dir)
    os.rename(filename, filename[:-3] + 'whl')
    rmtree(dir)

def main():
    parser = ArgumentParser()
    parser.add_argument('eggs', nargs='*', help="Eggs to convert")
    parser.add_argument('--dest-dir', '-d', default=os.path.curdir,
            help="Directory to store wheels (default %(default)s)")
    parser.add_argument('--verbose', '-v', action='store_true')
    args = parser.parse_args()
    for pat in args.eggs:
        for egg in iglob(pat):
            if args.verbose:
                sys.stdout.write("{0}... ".format(egg))
            egg2wheel(egg, args.dest_dir)
            if args.verbose:
                sys.stdout.write("OK\n")

if __name__ == "__main__":
    main()
