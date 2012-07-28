#!/usr/bin/env python
import os.path
import re
import sys
import sysconfig
import tempfile
import zipfile
import wheel.bdist_wheel
import distutils.dist
from distutils.archive_util import make_archive
from shutil import rmtree

egg_info_re = re.compile(r'''(?P<name>.+?)-(?P<ver>.+?)
    (-(?P<pyver>.+?))?(-(?P<arch>.+?))?.egg''', re.VERBOSE)

# bdist_wininst_info_re = re.compile(r'''^(?P<name>.+?)(-(?P<ver>.+?)\.)?
#     (?P<arch>\w+-\w+)-(?P<pyver>py\d.+).exe''', re.VERBOSE)


def bdist_wininst2wheel(path):
    base = os.path.splitext(os.path.basename(path))[0]
    info = dict()
    info['name'], sep, base = base.partition('-')
    base, sep, info['pyver'] = base.rpartition('-')
    if not sep:
        base = info['pyver']
        # This does not work, as the wheel filename format doesn't cater for
        # archives that are not Python version specific
        # info['pyver'] = 'any'
        impl_ver = sysconfig.get_config_var("py_version_nodot")
        if not impl_ver:
            impl_ver = ''.join(map(str, sys.version_info[:2]))
        info['pyver'] = 'py' + impl_ver
    info['ver'], sep, info['arch'] = base.rpartition('.')
    dist_info = "%(name)s-%(ver)s" % info
    datadir = "%s.data/" % dist_info

    # rewrite paths to trick ZipFile into extracting an egg
    # XXX grab wininst .ini - between .exe, padding, and first zip file.
    bdw = zipfile.ZipFile(path)
    root_is_purelib = True
    for zipinfo in bdw.infolist():
        if zipinfo.filename.startswith('PLATLIB'):
            root_is_purelib = False
            break
    if root_is_purelib:
        paths = {'purelib': ''}
    else:
        paths = {'platlib': ''}
    members = []
    for zipinfo in bdw.infolist():
        key, basename = zipinfo.filename.split('/', 1)
        key = key.lower()
        basepath = paths.get(key, None)
        if basepath is None:
            basepath = datadir + key.lower() + '/'
        oldname = zipinfo.filename
        newname = basepath + basename
        zipinfo.filename = newname
        del bdw.NameToInfo[oldname]
        bdw.NameToInfo[newname] = zipinfo
        # Collect member names, but omit '' (from an entry like "PLATLIB/"
        if newname:
            members.append(newname)
    dir = tempfile.mkdtemp(suffix="_b2w")
    bdw.extractall(dir, members)

    # egg2wheel
    abi = 'noabi'
    pyver = info['pyver'].replace('.', '')
    arch = (info['arch'] or 'noarch').replace('.', '_').replace('-', '_')
    if arch != 'noarch':
        # assume all binary eggs are for CPython
        pyver = 'cp' + pyver[2:]
    wheel_name = '-'.join((
                          dist_info,
                          pyver,
                          abi,
                          arch
                          ))
    bw = wheel.bdist_wheel.bdist_wheel(distutils.dist.Distribution())
    bw.root_is_purelib = root_is_purelib
    dist_info_dir = os.path.join(dir, '%s.dist-info' % dist_info)
    bw.egg2dist(os.path.join(dir,
                             "%(name)s-%(ver)s-%(pyver)s.egg-info" % info),
                dist_info_dir)
    bw.write_wheelfile(dist_info_dir, packager='egg2wheel')
    bw.write_record(dir, dist_info_dir)
    filename = make_archive(wheel_name, 'zip', root_dir=dir)
    os.rename(filename, filename[:-3] + 'whl')
    rmtree(dir)

def main():
    bdist_wininst2wheel(sys.argv[1])

if __name__ == "__main__":
    main()
