"""
Create a wheel (.whl) distribution.

A wheel is a built archive format.
"""

import distutils
import os
import shutil
import stat
import sys
import re
import warnings
from collections import OrderedDict
from distutils.core import Command
from distutils.sysconfig import get_config_var
from distutils import log as logger
from pathlib import Path
from shutil import rmtree
from typing import Set
from zipfile import ZIP_DEFLATED, ZIP_STORED

from packaging import tags
import pkg_resources

from .macosx_libfile import calculate_macosx_platform_tag
from .metadata import pkginfo_to_metadata
from .wheelfile import WheelFile, make_filename
from . import __version__ as wheel_version


safe_name = pkg_resources.safe_name
safe_version = pkg_resources.safe_version

PY_LIMITED_API_PATTERN = r'cp3\d'


def python_tag():
    return 'py{}'.format(sys.version_info[0])


def get_platform(archive_root):
    """Return our platform name 'win32', 'linux_x86_64'"""
    # XXX remove distutils dependency
    result = distutils.util.get_platform()
    if result.startswith("macosx") and archive_root is not None:
        result = calculate_macosx_platform_tag(archive_root, result)
    if result == "linux_x86_64" and sys.maxsize == 2147483647:
        # pip pull request #3497
        result = "linux_i686"

    return result


def get_flag(var, fallback, expected=True, warn=True):
    """Use a fallback value for determining SOABI flags if the needed config
    var is unset or unavailable."""
    val = get_config_var(var)
    if val is None:
        if warn:
            warnings.warn("Config variable '{0}' is unset, Python ABI tag may "
                          "be incorrect".format(var), RuntimeWarning, 2)

        return fallback

    return val == expected


def get_abi_tag():
    """Return the ABI tag based on SOABI (if available) or emulate SOABI
    (CPython 2, PyPy)."""
    soabi = get_config_var('SOABI')
    impl = tags.interpreter_name()
    if not soabi and impl in ('cp', 'pp') and hasattr(sys, 'maxunicode'):
        d = ''
        m = ''
        u = ''
        if get_flag('Py_DEBUG',
                    hasattr(sys, 'gettotalrefcount'),
                    warn=(impl == 'cp')):
            d = 'd'
        if get_flag('WITH_PYMALLOC',
                    impl == 'cp',
                    warn=(impl == 'cp' and
                          sys.version_info < (3, 8))) \
                and sys.version_info < (3, 8):
            m = 'm'
        if get_flag('Py_UNICODE_SIZE',
                    sys.maxunicode == 0x10ffff,
                    expected=4,
                    warn=(impl == 'cp' and
                          sys.version_info < (3, 3))) \
                and sys.version_info < (3, 3):
            u = 'u'
        abi = '%s%s%s%s%s' % (impl, tags.interpreter_version(), d, m, u)
    elif soabi and soabi.startswith('cpython-'):
        abi = 'cp' + soabi.split('-')[1]
    elif soabi:
        abi = soabi.replace('.', '_').replace('-', '_')
    else:
        abi = None

    return abi


def safer_name(name):
    return safe_name(name).replace('-', '_')


def safer_version(version):
    return safe_version(version).replace('-', '_')


def remove_readonly(func, path, excinfo):
    print(str(excinfo[1]))
    os.chmod(path, stat.S_IWRITE)
    func(path)


class bdist_wheel(Command):

    description = 'create a wheel distribution'

    supported_compressions = OrderedDict([
        ('stored', ZIP_STORED),
        ('deflated', ZIP_DEFLATED)
    ])

    user_options = [('bdist-dir=', 'b',
                     "temporary directory for creating the distribution"),
                    ('plat-name=', 'p',
                     "platform name to embed in generated filenames "
                     "(default: %s)" % get_platform(None)),
                    ('keep-temp', 'k',
                     "keep the pseudo-installation tree around after " +
                     "creating the distribution archive"),
                    ('dist-dir=', 'd',
                     "directory to put final built distributions in"),
                    ('skip-build', None,
                     "skip rebuilding everything (for testing/debugging)"),
                    ('relative', None,
                     "build the archive using relative paths "
                     "(default: false)"),
                    ('owner=', 'u',
                     "Owner name used when creating a tar file"
                     " [default: current user]"),
                    ('group=', 'g',
                     "Group name used when creating a tar file"
                     " [default: current group]"),
                    ('universal', None,
                     "make a universal wheel"
                     " (default: false)"),
                    ('compression=', None,
                     "zipfile compression (one of: {})"
                     " (default: 'deflated')"
                     .format(', '.join(supported_compressions))),
                    ('python-tag=', None,
                     "Python implementation compatibility tag"
                     " (default: '%s')" % (python_tag())),
                    ('build-number=', None,
                     "Build number for this particular version. "
                     "As specified in PEP-0427, this must start with a digit. "
                     "[default: None]"),
                    ('py-limited-api=', None,
                     "Python tag (cp32|cp33|cpNN) for abi3 wheel tag"
                     " (default: false)"),
                    ]

    boolean_options = ['keep-temp', 'skip-build', 'relative', 'universal']

    def initialize_options(self):
        self.bdist_dir = None
        self.data_dir = None
        self.plat_name = None
        self.plat_tag = None
        self.format = 'zip'
        self.keep_temp = False
        self.dist_dir = None
        self.egginfo_dir = None
        self.root_is_pure = None
        self.skip_build = None
        self.relative = False
        self.owner = None
        self.group = None
        self.universal = False
        self.compression = 'deflated'
        self.python_tag = python_tag()
        self.build_number = None
        self.py_limited_api = False
        self.plat_name_supplied = False

    def finalize_options(self):
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'wheel')

        self.data_dir = self.wheel_dist_name + '.data'
        self.plat_name_supplied = self.plat_name is not None

        try:
            self.compression = self.supported_compressions[self.compression]
        except KeyError:
            raise ValueError('Unsupported compression: {}'.format(self.compression))

        need_options = ('dist_dir', 'plat_name', 'skip_build')

        self.set_undefined_options('bdist',
                                   *zip(need_options, need_options))

        self.root_is_pure = not (self.distribution.has_ext_modules()
                                 or self.distribution.has_c_libraries())

        if self.py_limited_api and not re.match(PY_LIMITED_API_PATTERN, self.py_limited_api):
            raise ValueError("py-limited-api must match '%s'" % PY_LIMITED_API_PATTERN)

        # Support legacy [wheel] section for setting universal
        wheel = self.distribution.get_option_dict('wheel')
        if 'universal' in wheel:
            # please don't define this in your global configs
            logger.warn('The [wheel] section is deprecated. Use [bdist_wheel] instead.')
            val = wheel['universal'][1].strip()
            if val.lower() in ('1', 'true', 'yes'):
                self.universal = True

        if self.build_number is not None and not self.build_number[:1].isdigit():
            raise ValueError("Build tag (build-number) must start with a digit.")

    @property
    def wheel_dist_name(self):
        """Return distribution full name with - replaced with _"""
        components = (safer_name(self.distribution.get_name()),
                      safer_version(self.distribution.get_version()))
        if self.build_number:
            components += (self.build_number,)
        return '-'.join(components)

    def get_tag(self):
        # bdist sets self.plat_name if unset, we should only use it for purepy
        # wheels if the user supplied it.
        if self.plat_name_supplied:
            plat_name = self.plat_name
        elif self.root_is_pure:
            plat_name = 'any'
        else:
            # macosx contains system version in platform name so need special handle
            if self.plat_name and not self.plat_name.startswith("macosx"):
                plat_name = self.plat_name
            else:
                # on macosx always limit the platform name to comply with any
                # c-extension modules in bdist_dir, since the user can specify
                # a higher MACOSX_DEPLOYMENT_TARGET via tools like CMake

                # on other platforms, and on macosx if there are no c-extension
                # modules, use the default platform name.
                plat_name = get_platform(self.bdist_dir)

            if plat_name in ('linux-x86_64', 'linux_x86_64') and sys.maxsize == 2147483647:
                plat_name = 'linux_i686'

        plat_name = plat_name.replace('-', '_').replace('.', '_')

        if self.root_is_pure:
            if self.universal:
                impl = 'py2.py3'
            else:
                impl = self.python_tag
            tag = (impl, 'none', plat_name)
        else:
            impl_name = tags.interpreter_name()
            impl_ver = tags.interpreter_version()
            impl = impl_name + impl_ver
            # We don't work on CPython 3.1, 3.0.
            if self.py_limited_api and (impl_name + impl_ver).startswith('cp3'):
                impl = self.py_limited_api
                abi_tag = 'abi3'
            else:
                abi_tag = str(get_abi_tag()).lower()
            tag = (impl, abi_tag, plat_name)
            supported_tags = [(t.interpreter, t.abi, t.platform)
                              for t in tags.sys_tags()]
            assert tag in supported_tags, "would build wheel with unsupported tag {}".format(tag)
        return tag

    def run(self):
        build_scripts = self.reinitialize_command('build_scripts')
        build_scripts.executable = 'python'
        build_scripts.force = True

        build_ext = self.reinitialize_command('build_ext')
        build_ext.inplace = False

        if not self.skip_build:
            self.run_command('build')

        install = self.reinitialize_command('install',
                                            reinit_subcommands=True)
        install.root = self.bdist_dir
        install.compile = False
        install.skip_build = self.skip_build
        install.warn_dir = False

        # A wheel without setuptools scripts is more cross-platform.
        # Use the (undocumented) `no_ep` option to setuptools'
        # install_scripts command to avoid creating entry point scripts.
        install_scripts = self.reinitialize_command('install_scripts')
        install_scripts.no_ep = True

        # Use a custom scheme for the archive, because we have to decide
        # at installation time which scheme to use.
        for key in ('headers', 'scripts', 'data', 'purelib', 'platlib'):
            setattr(install,
                    'install_' + key,
                    os.path.join(self.data_dir, key))

        basedir_observed = ''

        if os.name == 'nt':
            # win32 barfs if any of these are ''; could be '.'?
            # (distutils.command.install:change_roots bug)
            basedir_observed = os.path.normpath(os.path.join(self.data_dir, '..'))
            self.install_libbase = self.install_lib = basedir_observed

        setattr(install,
                'install_purelib' if self.root_is_pure else 'install_platlib',
                basedir_observed)

        logger.info("installing to %s", self.bdist_dir)
        self.run_command('install')

        impl_tag, abi_tag, plat_tag = self.get_tag()
        archive_basename = make_filename(
            self.distribution.get_name(), self.distribution.get_version(),
            self.build_number, impl_tag, abi_tag, plat_tag
        )
        print('basename:', archive_basename)
        archive_root = Path(self.bdist_dir)
        if self.relative:
            archive_root /= self._ensure_relative(install.install_base)

        # Make the archive
        if not os.path.exists(self.dist_dir):
            os.makedirs(self.dist_dir)

        wheel_path = Path(self.dist_dir) / archive_basename
        logger.info("creating '%s' and adding '%s' to it", wheel_path, archive_root)
        with WheelFile(wheel_path, 'w', compression=self.compression,
                       generator='bdist_wheel (' + wheel_version + ')',
                       root_is_purelib=self.root_is_pure) as wf:
            deferred = []
            for root, dirnames, filenames in os.walk(str(archive_root)):
                # Sort the directory names so that `os.walk` will walk them in a
                # defined order on the next iteration.
                dirnames.sort()
                root_path = archive_root / root
                if root_path.name.endswith('.egg-info'):
                    continue

                for name in sorted(filenames):
                    path = root_path / name
                    if path.is_file():
                        archive_name = str(path.relative_to(archive_root))
                        if root.endswith('.dist-info'):
                            deferred.append((path, archive_name))
                        else:
                            logger.info("adding '%s'", archive_name)
                            wf.write_file(archive_name, path.read_bytes())

            for path, archive_name in sorted(deferred):
                logger.info("adding '%s'", archive_name)
                wf.write_file(archive_name, path.read_bytes())

            # Write the license files
            for license_path in self.license_paths:
                logger.info("adding '%s'", license_path)
                wf.write_distinfo_file(os.path.basename(license_path), license_path.read_bytes())

            # Write the metadata files from the .egg-info directory
            self.set_undefined_options('install_egg_info', ('target', 'egginfo_dir'))
            for path in Path(self.egginfo_dir).iterdir():
                if path.name == 'PKG-INFO':
                    items = pkginfo_to_metadata(path)
                    wf.write_metadata(items)
                elif path.name not in {'requires.txt', 'SOURCES.txt', 'not-zip-safe',
                                       'dependency_links.txt'}:
                    wf.write_distinfo_file(path.name, path.read_bytes())

        shutil.rmtree(self.egginfo_dir)

        # Add to 'Distribution.dist_files' so that the "upload" command works
        getattr(self.distribution, 'dist_files', []).append(
            ('bdist_wheel',
             '{}.{}'.format(*sys.version_info[:2]),  # like 3.7
             str(wheel_path)))

        if not self.keep_temp:
            logger.info('removing %s', self.bdist_dir)
            if not self.dry_run:
                rmtree(self.bdist_dir, onerror=remove_readonly)

    def _ensure_relative(self, path: str) -> str:
        # copied from dir_util, deleted
        drive, path = os.path.splitdrive(path)
        if path[0:1] == os.sep:
            path = drive + path[1:]
        return path

    @property
    def license_paths(self) -> Set[Path]:
        metadata = self.distribution.get_option_dict('metadata')
        files = set()  # type: Set[Path]
        patterns = sorted({
            option for option in metadata.get('license_files', ('', ''))[1].split()
        })

        if 'license_file' in metadata:
            warnings.warn('The "license_file" option is deprecated. Use '
                          '"license_files" instead.', DeprecationWarning)
            files.add(Path(metadata['license_file'][1]))

        if 'license_file' not in metadata and 'license_files' not in metadata:
            patterns = ('LICEN[CS]E*', 'COPYING*', 'NOTICE*', 'AUTHORS*')

        for pattern in patterns:
            for path in Path().glob(pattern):
                if path.name.endswith('~'):
                    logger.debug('ignoring license file "%s" as it looks like a backup', path)
                    continue

                if path not in files and path.is_file():
                    logger.info('adding license file "%s" (matched pattern "%s")', path, pattern)
                    files.add(path)

        return files

    # def egg2dist(self, egginfo_path, distinfo_path):
    #     """Convert an .egg-info directory into a .dist-info directory"""
    #     def adios(p):
    #         """Appropriately delete directory, file or link."""
    #         if os.path.exists(p) and not os.path.islink(p) and os.path.isdir(p):
    #             shutil.rmtree(p)
    #         elif os.path.exists(p):
    #             os.unlink(p)
    #
    #     adios(distinfo_path)
    #
    #     if not os.path.exists(egginfo_path):
    #         # There is no egg-info. This is probably because the egg-info
    #         # file/directory is not named matching the distribution name used
    #         # to name the archive file. Check for this case and report
    #         # accordingly.
    #         import glob
    #         pat = os.path.join(os.path.dirname(egginfo_path), '*.egg-info')
    #         possible = glob.glob(pat)
    #         err = "Egg metadata expected at %s but not found" % (egginfo_path,)
    #         if possible:
    #             alt = os.path.basename(possible[0])
    #             err += " (%s found - possible misnamed archive file?)" % (alt,)
    #
    #         raise ValueError(err)
    #
    #     if os.path.isfile(egginfo_path):
    #         # .egg-info is a single file
    #         pkginfo_path = egginfo_path
    #         pkg_info = pkginfo_to_metadata(egginfo_path)
    #         os.mkdir(distinfo_path)
    #     else:
    #         # .egg-info is a directory
    #         pkginfo_path = os.path.join(egginfo_path, 'PKG-INFO')
    #         pkg_info = pkginfo_to_metadata(egginfo_path)
    #
    #         # ignore common egg metadata that is useless to wheel
    #         shutil.copytree(egginfo_path, distinfo_path,
    #                         ignore=lambda x, y: {'PKG-INFO', 'requires.txt', 'SOURCES.txt',
    #                                              'not-zip-safe'}
    #                         )
    #
    #         # delete dependency_links if it is only whitespace
    #         dependency_links_path = os.path.join(distinfo_path, 'dependency_links.txt')
    #         with open(dependency_links_path, 'r') as dependency_links_file:
    #             dependency_links = dependency_links_file.read().strip()
    #         if not dependency_links:
    #             adios(dependency_links_path)
    #
    #     write_pkg_info(os.path.join(distinfo_path, 'METADATA'), pkg_info)
    #
    #     for license_path in self.license_paths:
    #         filename = os.path.basename(license_path)
    #         shutil.copy(license_path, os.path.join(distinfo_path, filename))
    #
    #     adios(egginfo_path)
