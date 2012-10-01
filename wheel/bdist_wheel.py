"""Create a wheel (.whl) distribution.

A wheel is a built archive format.
"""

import csv
import hashlib
import os
import subprocess
import warnings

try:
    import sysconfig
except ImportError:  # pragma nocover
    # Python < 2.7
    import distutils.sysconfig as sysconfig

try:
    import pkg_resources
except ImportError:
    # this dance makes the unit tests happy
    # bdist_wheel won't really work without distribute
    from wheel import pkg_resources
    
safe_name = pkg_resources.safe_name
safe_version = pkg_resources.safe_version

from shutil import rmtree
from email.generator import Generator

from distutils.util import get_platform
from distutils.core import Command
from distutils.sysconfig import get_python_version

from distutils import log as logger
import shutil

from .util import get_abbr_impl, get_impl_ver, native, open_for_csv
from .archive import archive_wheelfile
from .pkginfo import read_pkg_info, write_pkg_info

def safer_name(name):
    return safe_name(name).replace('-', '_')


def safer_version(version):
    return safe_version(version).replace('-', '_')


class bdist_wheel(Command):

    description = 'create a wheel distribution'

    user_options = [('bdist-dir=', 'b',
                     "temporary directory for creating the distribution"),
                    ('plat-name=', 'p',
                     "platform name to embed in generated filenames "
                     "(default: %s)" % get_platform()),
                    ('keep-temp', 'k',
                     "keep the pseudo-installation tree around after " +
                     "creating the distribution archive"),
                    ('dist-dir=', 'd',
                     "directory to put final built distributions in"),
                    ('skip-build', None,
                     "skip rebuilding everything (for testing/debugging)"),
                    ('relative', None,
                     "build the archive using relative paths"
                     "(default: false)"),
                    ('owner=', 'u',
                     "Owner name used when creating a tar file"
                     " [default: current user]"),
                    ('group=', 'g',
                     "Group name used when creating a tar file"
                     " [default: current group]"),
                    ]

    boolean_options = ['keep-temp', 'skip-build', 'relative']

    def initialize_options(self):
        self.bdist_dir = None
        self.data_dir = None
        self.plat_name = None
        self.format = 'zip'
        self.keep_temp = False
        self.dist_dir = None
        self.distinfo_dir = None
        self.egginfo_dir = None
        self.root_is_purelib = None
        self.skip_build = None
        self.relative = False
        self.owner = None
        self.group = None

    def finalize_options(self):
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command('bdist').bdist_base
            self.bdist_dir = os.path.join(bdist_base, 'wheel')

        self.data_dir = self.wheel_dist_name + '.data'

        need_options = ('dist_dir', 'plat_name', 'skip_build')

        self.set_undefined_options('bdist',
                                   *zip(need_options, need_options))

        self.root_is_purelib = self.distribution.is_pure()

    @property
    def wheel_dist_name(self):
        """Return distribution full name with - replaced with _"""
        return '-'.join((safer_name(self.distribution.get_name()),
                         safer_version(self.distribution.get_version())))

    def get_archive_basename(self):
        """Return archive name without extension"""
        purity = self.distribution.is_pure()
        impl_ver = get_impl_ver()
        abi_tag = 'none'
        plat_name = 'any'
        impl_name = 'py'
        if purity:
            wheel = self.distribution.get_option_dict('wheel')
            if 'universal' in wheel:
                # please don't define this in your global configs
                val = wheel['universal'][1].split('#', 1)[0].strip()
                if val == '1':
                    impl_name = 'py2.py3'
                    impl_ver = ''
        else:
            plat_name = self.plat_name.replace('-', '_').replace('.', '_')
            impl_name = get_abbr_impl()
            # PEP 3149 -- no SOABI in Py 2
            # For PyPy?
            # "pp%s%s" % (sys.pypy_version_info.major,
            # sys.pypy_version_info.minor)
            abi_tag = sysconfig.get_config_vars().get('SOABI', abi_tag)
            abi_tag = abi_tag.rsplit('-', 1)[-1]
        archive_basename = "%s-%s%s-%s-%s" % (
            self.wheel_dist_name,
            impl_name,
            impl_ver,
            abi_tag,
            plat_name)
        return archive_basename

    def run(self):
        build_scripts = self.reinitialize_command('build_scripts')
        build_scripts.executable = 'python'

        if not self.skip_build:
            self.run_command('build')

        install = self.reinitialize_command('install',
                                            reinit_subcommands=True)
        install.root = self.bdist_dir
        install.compile = False
        install.skip_build = self.skip_build
        install.warn_dir = False

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
            basedir_observed = os.path.join(self.data_dir, '..')
            self.install_libbase = self.install_lib = basedir_observed

        setattr(install,
                ('install_platlib', 'install_purelib')[self.root_is_purelib],
                basedir_observed)

        logger.info("installing to %s", self.bdist_dir)
        
        self.run_command('install')

        archive_basename = self.get_archive_basename()

        pseudoinstall_root = os.path.join(self.dist_dir, archive_basename)
        if not self.relative:
            archive_root = self.bdist_dir
        else:
            archive_root = os.path.join(
                self.bdist_dir,
                self._ensure_relative(install.install_base))

        self.set_undefined_options(
            'install_egg_info', ('target', 'egginfo_dir'))
        self.distinfo_dir = os.path.join(self.bdist_dir,
                                         '%s.dist-info' % self.wheel_dist_name)
        self.egg2dist(self.egginfo_dir,
                      self.distinfo_dir)
                
        metadata_path = os.path.join(self.distinfo_dir, 'METADATA')
        self.add_requirements(metadata_path)

        self.write_wheelfile(self.distinfo_dir)

        self.write_record(self.bdist_dir, self.distinfo_dir)

        # Make the archive
        if not os.path.exists(self.dist_dir):
            os.makedirs(self.dist_dir)
        wheel_name = archive_wheelfile(pseudoinstall_root, archive_root)
        
        # Sign the archive
        if 'WHEEL_TOOL' in os.environ:
            subprocess.call([os.environ['WHEEL_TOOL'], 'sign', wheel_name])

        # Add to 'Distribution.dist_files' so that the "upload" command works
        getattr(self.distribution, 'dist_files', []).append(
            ('bdist_wheel', get_python_version(), wheel_name))

        if not self.keep_temp:
            if self.dry_run:
                logger.info('removing %s', self.bdist_dir)
            else:
                rmtree(self.bdist_dir)

    def write_wheelfile(self, wheelfile_base, generator='bdist_wheel'):
        from email.message import Message
        msg = Message()
        msg['Wheel-Version'] = '0.1'  # of the spec
        msg['Generator'] = generator
        msg['Root-Is-Purelib'] = str(self.root_is_purelib).lower()
        wheelfile_path = os.path.join(wheelfile_base, 'WHEEL')
        logger.info('creating %s', wheelfile_path)
        with open(wheelfile_path, 'w') as f:
            Generator(f, maxheaderlen=0).flatten(msg)

    def _ensure_relative(self, path):
        # copied from dir_util, deleted
        drive, path = os.path.splitdrive(path)
        if path[0:1] == os.sep:
            path = drive + path[1:]
        return path

    def _to_requires_dist(self, requirement):
        requires_dist = []
        for op, ver in requirement.specs:
            # PEP 345 specifies but does not use == as part of a version spec
            if op == '==':
                op = ''
            requires_dist.append(op + ver)
        if not requires_dist:
            return ''
        return " (%s)" % ','.join(requires_dist)

    def _pkginfo_to_metadata(self, egg_info_path, pkginfo_path):
        pkg_info = read_pkg_info(pkginfo_path)
        pkg_info.replace_header('Metadata-Version', '1.3')
        requires_path = os.path.join(egg_info_path, 'requires.txt')
        if os.path.exists(requires_path):
            requires = open(requires_path).read()
            for extra, reqs in pkg_resources.split_sections(requires):
                condition = ''
                if extra:
                    pkg_info['Provides-Extra'] = extra
                    condition = '; extra == %s' % repr(extra)
                for req in reqs:
                    parsed_requirement = pkg_resources.Requirement.parse(req)
                    spec = self._to_requires_dist(parsed_requirement)
                    pkg_info['Requires-Dist'] = parsed_requirement.key + \
                        spec + condition
        return pkg_info
    
    def setupcfg_requirements(self):
        """Generate requirements from setup.cfg as 
        ('Requires-Dist', 'requirement; qualifier') tuples. From a metadata
        section in setup.cfg:
        
        [metadata]
        provides-extra = extra1
            extra2
        requires-dist = requirement; qualifier
            another; qualifier2
            unqualified
            
        Yields
        
        ('Provides-Extra', 'extra1'),
        ('Provides-Extra', 'extra2'),
        ('Requires-Dist', 'requirement; qualifier'),
        ('Requires-Dist', 'another; qualifier2'),
        ('Requires-Dist', 'unqualified')
        """
        metadata = self.distribution.get_option_dict('metadata')

        # our .ini parser folds - to _ in key names:
        for key, title in (('provides_extra', 'Provides-Extra'), 
                           ('requires_dist', 'Requires-Dist')):
            if not key in metadata:
                continue
            field = metadata[key]
            for line in field[1].splitlines():
                line = line.strip()
                if not line:
                    continue
                yield (title, line) 
    
    def add_requirements(self, metadata_path):
        """Add additional requirements from setup.cfg to file metadata_path"""
        additional = list(self.setupcfg_requirements())
        if not additional: return        
        pkg_info = read_pkg_info(metadata_path)
        if 'Provides-Extra' in pkg_info or 'Requires-Dist' in pkg_info:
            warnings.warn('setup.cfg requirements overwrite values from setup.py')
            del pkg_info['Provides-Extra']
            del pkg_info['Requires-Dist'] 
        for k, v in additional:
            pkg_info[k] = v
        write_pkg_info(metadata_path, pkg_info)
        
    def egg2dist(self, egginfo_path, distinfo_path):
        """Convert an .egg-info directory into a .dist-info directory"""
        def adios(p):
            """Appropriately delete directory, file or link."""
            if os.path.exists(p) and not os.path.islink(p) and os.path.isdir(p):
                shutil.rmtree(p)
            elif os.path.exists(p):
                os.unlink(p)

        adios(distinfo_path)

        if not os.path.exists(egginfo_path):
            # There is no egg-info. This is probably because the egg-info
            # file/directory is not named matching the distribution name used
            # to name the archive file. Check for this case and report
            # accordingly.
            import glob
            pat = os.path.join(os.path.dirname(egginfo_path), '*.egg-info')
            possible = glob.glob(pat)
            err = "Egg metadata expected at %s but not found" % (egginfo_path,)
            if possible:
                alt = os.path.basename(possible[0])
                err += " (%s found - possible misnamed archive file?)" % (alt,)

            raise ValueError(err)

        if os.path.isfile(egginfo_path):
            # .egg-info is a single file
            pkginfo_path = egginfo_path
            pkg_info = self._pkginfo_to_metadata(egginfo_path, egginfo_path)
            os.mkdir(distinfo_path)
        else:
            # .egg-info is a directory
            pkginfo_path = os.path.join(egginfo_path, 'PKG-INFO')
            pkg_info = self._pkginfo_to_metadata(egginfo_path, pkginfo_path)

            # ignore common egg metadata that is useless to wheel
            shutil.copytree(egginfo_path, distinfo_path,
                            ignore=lambda x, y: set(('PKG-INFO', 
                                                     'requires.txt',
                                                     'SOURCES.txt',
                                                     'not-zip-safe',)))
            
            # delete dependency_links if it is only whitespace
            dependency_links = os.path.join(distinfo_path, 'dependency_links.txt')
            if not open(dependency_links, 'r').read().strip(): 
                adios(dependency_links)        

        write_pkg_info(os.path.join(distinfo_path, 'METADATA'), pkg_info)

        adios(egginfo_path)

    def write_record(self, bdist_dir, distinfo_dir):
        from wheel.util import urlsafe_b64encode

        record_path = os.path.join(distinfo_dir, 'RECORD')
        record_relpath = os.path.relpath(record_path, bdist_dir)

        def walk():
            for dir, dirs, files in os.walk(bdist_dir):
                for f in files:
                    yield os.path.join(dir, f)

        def skip(path):
            return (path.endswith('.pyc')
                    or path.endswith('.pyo') or path == record_relpath)

        writer = csv.writer(open_for_csv(record_path, 'w+'))
        for path in walk():
            relpath = os.path.relpath(path, bdist_dir)
            if skip(relpath):
                hash = ''
                size = ''
            else:
                data = open(path, 'rb').read()
                digest = hashlib.sha256(data).digest()
                hash = 'sha256='+native(urlsafe_b64encode(digest))
                size = len(data)
            record_path = os.path.relpath(
                path, bdist_dir).replace(os.path.sep, '/')
            writer.writerow((record_path, hash, size))
