"""Create a wheel (.whl) distribution.

A wheel is a built archive that decouples the build and install process. 
"""

import os
import sys
import sysconfig
import pkg_resources
from shutil import rmtree
from email.parser import Parser

from distutils.util import get_platform
from distutils.core import Command

from distutils import log as logger
import shutil

class bdist_wheel(Command):

    description = 'create a wheel distribution'

    user_options = [('bdist-dir=', 'd',
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
             
        self.data_dir = os.path.join(self.bdist_dir, 
                                     self.distribution.get_fullname() + '.data')
        
        need_options = ('dist_dir', 'plat_name', 'skip_build')
        
        self.set_undefined_options('bdist',
                                   *zip(need_options, need_options))
        
        self.root_is_purelib = self.distribution.is_pure()        

    def get_abbr_impl(self):
        """Return abbreviated implementation name"""
        if hasattr(sys, 'pypy_version_info'):
            pyimpl = 'pp'
        elif sys.platform.startswith('java'):
            pyimpl = 'jy'
        elif sys.platform == 'cli':
            pyimpl = 'ip'
        else:
            pyimpl = 'cp'
        return pyimpl

    def get_archive_basename(self):
        """Return archive name without extension"""
        purity = self.distribution.is_pure()
        if purity:
            plat_name = 'noarch'
            impl_name = 'py'
            abi_tag = sysconfig.get_config_var("py_version_nodot")
        else:
            plat_name = self.plat_name.replace('-', '_').replace('.', '_')
            impl_name = self.get_abbr_impl()
            abi_tag = sysconfig.get_config_var('SOABI').rsplit('-', 1)[-1]
        archive_basename = "%s-%s%s-%s" % (
                self.distribution.get_fullname(),
                impl_name,
                abi_tag,
                plat_name)
        return archive_basename

    def run(self):
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
                        
        if self.root_is_purelib:
            setattr(install,
                   'install_purelib',
                   '')
        else:
            setattr(install,
                    'install_platlib',
                    '')

        logger.info("installing to %s", self.bdist_dir)
        if False:
            self.fixup_data_files()
        self.run_command('install')

        archive_basename = self.get_archive_basename()

        # OS/2 objects to any ":" characters in a filename (such as when
        # a timestamp is used in a version) so change them to hyphens.
        if os.name == "os2":
            archive_basename = archive_basename.replace(":", "-")

        pseudoinstall_root = os.path.join(self.dist_dir, archive_basename)
        if not self.relative:
            archive_root = self.bdist_dir
        else:
            archive_root = os.path.join(
                self.bdist_dir,
                self._ensure_relative(install.install_base))

        self.set_undefined_options('install_egg_info', ('target', 'egginfo_dir'))
        self.distinfo_dir = os.path.join(self.bdist_dir, 
                                         '%s.dist-info' % self.distribution.get_fullname())
        self.egg2dist(self.egginfo_dir, 
                      self.distinfo_dir)

        self.write_wheelfile(self.distinfo_dir)

        # Make the archive
        filename = self.make_archive(pseudoinstall_root,
                                     self.format, root_dir=archive_root,
                                     owner=self.owner, group=self.group)
        
        os.rename(filename, filename[:-3] + 'whl')

        if not self.keep_temp:
            if self.dry_run:
                logger.info('removing %s', self.bdist_dir)
            else:
                rmtree(self.bdist_dir)
                
    def write_wheelfile(self, wheelfile_base):
        from email.message import Message
        msg = Message()
        msg['Wheel-Version'] = '0.1'
        msg['Packager'] = 'packaging'
        msg['Root-Is-Purelib'] = str(self.root_is_purelib).lower()
        wheelfile_path = os.path.join(wheelfile_base, 'WHEEL')
        logger.info('creating %s', wheelfile_path)
        with open(wheelfile_path, 'w') as f:
            f.write(msg.as_string())
                
    def fixup_data_files(self):
        """Put all resources in a .data directory"""
        # (only useful in the packaging/distutils2 version of bdist_wheel)
        data_files = {}
        for k, v in self.distribution.data_files.items():
            # {dist-info} is already in our directory tree
            if v.startswith('{') and not v.startswith('{dist-info}'):
                # XXX assert valid (in sysconfig.get_paths() or 'distribution.name')
                data_files[k] = os.path.join(self.data_dir,
                                             v.replace('{', '').replace('}', ''))
        self.distribution.data_files.update(data_files)

    def _ensure_relative(self, path):
        # copied from dir_util, deleted
        drive, path = os.path.splitdrive(path)
        if path[0:1] == os.sep:
            path = drive + path[1:]
        return path
    
    def _to_requires_dist(self, requirement):
        requires_dist = []        
        for op, ver in requirement.specs:
            if op == '==':
                op = ''
            requires_dist.append(op + ver)
        return "(%s)" % ','.join(requires_dist)
    
    def _pkginfo_to_metadata(self, egg_info_path, pkginfo_path):
        # XXX Parser() doesn't preserve \n in field values
        pkg_info = Parser().parse(open(pkginfo_path))
        requires = open(os.path.join(egg_info_path, 'requires.txt')).read()        
        for extra, reqs in pkg_resources.split_sections(requires):
            if extra:
                continue # XXX no extras
            for req in reqs:
                parsed_requirement = pkg_resources.Requirement.parse(req)
                spec = self._to_requires_dist(parsed_requirement)
                pkg_info['Requires-Dist'] = parsed_requirement.key + " " + spec
        return pkg_info
    
    def egg2dist(self, egginfo_path, dist_info_path):
        """Convert an .egg-info directory into a .dist-info directory"""
        pkginfo_path = os.path.join(egginfo_path, 'PKG-INFO')
        pkg_info = self._pkginfo_to_metadata(egginfo_path, pkginfo_path)
        
        if not os.path.exists(dist_info_path):
            os.mkdir(dist_info_path)
            
        with open(os.path.join(dist_info_path, 'METADATA'), 'w') as metadata:
            metadata.write(pkg_info.as_string())

        shutil.rmtree(egginfo_path)
