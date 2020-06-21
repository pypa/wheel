import re
import shutil
import sys
import tempfile
import zipfile
from distutils import dist
from pathlib import Path
from typing import Union, Dict, Iterable

from wheel.wheelfile import make_filename

from ..bdist_wheel import bdist_wheel
from ..wheelfile import WheelFile
from . import WheelError, require_pkgresources

if sys.version_info >= (3, 6):
    from os import PathLike
else:
    PathLike = Path

egg_info_re = re.compile(r'''
    (?P<name>.+?)-(?P<ver>.+?)
    (-(?P<pyver>py\d\.\d+)
     (-(?P<arch>.+?))?
    )?.egg$''', re.VERBOSE)


class _bdist_wheel_tag(bdist_wheel):
    # allow the client to override the default generated wheel tag
    # The default bdist_wheel implementation uses python and abi tags
    # of the running python process. This is not suitable for
    # generating/repackaging prebuild binaries.

    full_tag_supplied = False
    full_tag = None  # None or a (pytag, soabitag, plattag) triple

    def get_tag(self):
        if self.full_tag_supplied and self.full_tag is not None:
            return self.full_tag
        else:
            return bdist_wheel.get_tag(self)


def egg2wheel(egg_path: Union[str, PathLike], dest_dir: Union[str, PathLike]) -> None:
    egg_path = Path(egg_path)
    dest_dir = Path(dest_dir)
    match = egg_info_re.match(egg_path.name)
    if not match:
        raise WheelError('Invalid egg file name: {}'.format(egg_path.name))

    egg_info = match.groupdict()
    tmp_path = Path(tempfile.mkdtemp(suffix="_e2w"))
    if egg_path.is_file():
        # assume we have a bdist_egg otherwise
        with zipfile.ZipFile(str(egg_path)) as egg:
            egg.extractall(str(tmp_path))
    else:
        # support buildout-style installed eggs directories
        for pth in egg_path.iterdir():
            if pth.is_file():
                shutil.copy2(str(pth), tmp_path)
            else:
                shutil.copytree(str(pth), tmp_path / pth.name)

    pyver = egg_info['pyver']
    if pyver:
        pyver = egg_info['pyver'] = pyver.replace('.', '')

    arch = (egg_info['arch'] or 'any').replace('.', '_').replace('-', '_')

    # assume all binary eggs are for CPython
    abi = 'cp' + pyver[2:] if arch != 'any' else 'none'

    root_is_purelib = egg_info['arch'] is None
    if root_is_purelib:
        bw = bdist_wheel(dist.Distribution())
    else:
        bw = _bdist_wheel_tag(dist.Distribution())

    bw.root_is_pure = root_is_purelib
    bw.python_tag = pyver
    bw.plat_name_supplied = True
    bw.plat_name = egg_info['arch'] or 'any'
    if not root_is_purelib:
        bw.full_tag_supplied = True
        bw.full_tag = (pyver, abi, arch)

    dist_info_dir = tmp_path / '{name}-{ver}.dist-info'.format(**egg_info)
    bw.egg2dist(tmp_path / 'EGG-INFO', dist_info_dir)
    wheel_name = make_filename(egg_info['name'], egg_info['ver'], impl_tag=pyver,
                               abi_tag=abi, plat_tag=arch)
    with WheelFile(dest_dir / wheel_name, 'w', generator='egg2wheel') as wf:
        wf.write_files(tmp_path)

    shutil.rmtree(str(tmp_path))


def parse_wininst_info(wininfo_name: str, egginfo_name: str) -> Dict[str, str]:
    """Extract metadata from filenames.

    Extracts the 4 metadataitems needed (name, version, pyversion, arch) from
    the installer filename and the name of the egg-info directory embedded in
    the zipfile (if any).

    The egginfo filename has the format::

        name-ver(-pyver)(-arch).egg-info

    The installer filename has the format::

        name-ver.arch(-pyver).exe

    Some things to note:

    1. The installer filename is not definitive. An installer can be renamed
       and work perfectly well as an installer. So more reliable data should
       be used whenever possible.
    2. The egg-info data should be preferred for the name and version, because
       these come straight from the distutils metadata, and are mandatory.
    3. The pyver from the egg-info data should be ignored, as it is
       constructed from the version of Python used to build the installer,
       which is irrelevant - the installer filename is correct here (even to
       the point that when it's not there, any version is implied).
    4. The architecture must be taken from the installer filename, as it is
       not included in the egg-info data.
    5. Architecture-neutral installers still have an architecture because the
       installer format itself (being executable) is architecture-specific. We
       should therefore ignore the architecture if the content is pure-python.
    """

    egginfo = None
    if egginfo_name:
        egginfo = egg_info_re.search(egginfo_name)
        if not egginfo:
            raise ValueError("Egg info filename %s is not valid" % (egginfo_name,))

    # Parse the wininst filename
    # 1. Distribution name (up to the first '-')
    w_name, sep, rest = wininfo_name.partition('-')
    if not sep:
        raise ValueError("Installer filename %s is not valid" % (wininfo_name,))

    # Strip '.exe'
    rest = rest[:-4]
    # 2. Python version (from the last '-', must start with 'py')
    rest2, sep, w_pyver = rest.rpartition('-')
    if sep and w_pyver.startswith('py'):
        rest = rest2
        w_pyver = w_pyver.replace('.', '')
    else:
        # Not version specific - use py2.py3. While it is possible that
        # pure-Python code is not compatible with both Python 2 and 3, there
        # is no way of knowing from the wininst format, so we assume the best
        # here (the user can always manually rename the wheel to be more
        # restrictive if needed).
        w_pyver = 'py2.py3'
    # 3. Version and architecture
    w_ver, sep, w_arch = rest.rpartition('.')
    if not sep:
        raise ValueError("Installer filename %s is not valid" % (wininfo_name,))

    if egginfo:
        w_name = egginfo.group('name')
        w_ver = egginfo.group('ver')

    return {'name': w_name, 'ver': w_ver, 'arch': w_arch, 'pyver': w_pyver}


def wininst2wheel(path: Union[str, PathLike], dest_dir: Union[str, PathLike]) -> None:
    with zipfile.ZipFile(str(path)) as bdw:
        # Search for egg-info in the archive
        egginfo_name = None
        for filename in bdw.namelist():
            if '.egg-info' in filename:
                egginfo_name = filename
                break

        info = parse_wininst_info(path.name, egginfo_name)

        root_is_purelib = True
        for zipinfo in bdw.infolist():
            if zipinfo.filename.startswith('PLATLIB'):
                root_is_purelib = False
                break
        if root_is_purelib:
            paths = {'purelib': ''}
        else:
            paths = {'platlib': ''}

        dist_info = "%(name)s-%(ver)s" % info
        datadir = "%s.data/" % dist_info

        # rewrite paths to trick ZipFile into extracting an egg
        # XXX grab wininst .ini - between .exe, padding, and first zip file.
        members = []
        egginfo_name = ''
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
            # Remember egg-info name for the egg2dist call below
            if not egginfo_name:
                if newname.endswith('.egg-info'):
                    egginfo_name = newname
                elif '.egg-info/' in newname:
                    egginfo_name, sep, _ = newname.rpartition('/')
        tmp_path = Path(tempfile.mkdtemp(suffix="_b2w"))
        bdw.extractall(tmp_path, members)

    # egg2wheel
    abi = 'none'
    pyver = info['pyver']
    arch = (info['arch'] or 'any').replace('.', '_').replace('-', '_')
    # Wininst installers always have arch even if they are not
    # architecture-specific (because the format itself is).
    # So, assume the content is architecture-neutral if root is purelib.
    if root_is_purelib:
        arch = 'any'
    # If the installer is architecture-specific, it's almost certainly also
    # CPython-specific.
    if arch != 'any':
        pyver = pyver.replace('py', 'cp')

    wheel_name = make_filename(info['name'], info['ver'], None, pyver, abi, arch)
    if root_is_purelib:
        bw = bdist_wheel(dist.Distribution())
    else:
        bw = _bdist_wheel_tag(dist.Distribution())

    bw.root_is_pure = root_is_purelib
    bw.python_tag = pyver
    bw.plat_name_supplied = True
    bw.plat_name = info['arch'] or 'any'

    if not root_is_purelib:
        bw.full_tag_supplied = True
        bw.full_tag = (pyver, abi, arch)

    dist_info_dir = tmp_path / '%s.dist-info' % dist_info
    bw.egg2dist(tmp_path / egginfo_name, dist_info_dir)

    with WheelFile(dest_dir / wheel_name, 'w', generator='wininst2wheel') as wf:
        wf.write_files(tmp_path)

    shutil.rmtree(str(tmp_path))


def convert(files: Iterable[str], dest_dir: Union[str, PathLike], verbose: bool) -> None:
    # Only support wheel convert if pkg_resources is present
    require_pkgresources('wheel convert')

    for pattern in files:
        for installer_path in Path.cwd().glob(pattern):
            if installer_path.suffix == '.egg':
                conv = egg2wheel
            else:
                conv = wininst2wheel

            if verbose:
                print("{}... ".format(installer_path))
                sys.stdout.flush()

            conv(installer_path, dest_dir)
            if verbose:
                print("OK")
