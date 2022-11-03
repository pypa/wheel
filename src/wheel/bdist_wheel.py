"""
Create a wheel (.whl) distribution.

A wheel is a built archive format.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import sys
import sysconfig
import warnings
from collections import OrderedDict
from email.generator import BytesGenerator, Generator
from glob import iglob
from io import BytesIO
from shutil import rmtree
from sysconfig import get_config_var
from zipfile import ZIP_DEFLATED, ZIP_STORED

import pkg_resources
from setuptools import Command

from . import __version__ as wheel_version
from .macosx_libfile import calculate_macosx_platform_tag
from .metadata import pkginfo_to_metadata
from .util import log
from .vendored.packaging import tags
from .wheelfile import WheelFile

safe_name = pkg_resources.safe_name
safe_version = pkg_resources.safe_version
setuptools_major_version = int(
    pkg_resources.get_distribution("setuptools").version.split(".")[0]
)

PY_LIMITED_API_PATTERN = r"cp3\d"


def python_tag():
    return f"py{sys.version_info[0]}"


def get_platform(archive_root):
    """Return our platform name 'win32', 'linux_x86_64'"""
    result = sysconfig.get_platform()
    if result.startswith("macosx") and archive_root is not None:
        result = calculate_macosx_platform_tag(archive_root, result)
    elif result == "linux-x86_64" and sys.maxsize == 2147483647:
        # pip pull request #3497
        result = "linux-i686"

    return result.replace("-", "_")


def get_flag(var, fallback, expected=True, warn=True):
    """Use a fallback value for determining SOABI flags if the needed config
    var is unset or unavailable."""
    val = get_config_var(var)
    if val is None:
        if warn:
            warnings.warn(
                "Config variable '{}' is unset, Python ABI tag may "
                "be incorrect".format(var),
                RuntimeWarning,
                2,
            )
        return fallback
    return val == expected


def get_abi_tag():
    """Return the ABI tag based on SOABI (if available) or emulate SOABI (PyPy)."""
    soabi = get_config_var("SOABI")
    impl = tags.interpreter_name()
    if not soabi and impl in ("cp", "pp") and hasattr(sys, "maxunicode"):
        d = ""
        m = ""
        u = ""
        if get_flag("Py_DEBUG", hasattr(sys, "gettotalrefcount"), warn=(impl == "cp")):
            d = "d"

        if get_flag(
            "WITH_PYMALLOC",
            impl == "cp",
            warn=(impl == "cp" and sys.version_info < (3, 8)),
        ) and sys.version_info < (3, 8):
            m = "m"

        abi = f"{impl}{tags.interpreter_version()}{d}{m}{u}"
    elif soabi and soabi.startswith("cpython-"):
        abi = "cp" + soabi.split("-")[1]
    elif soabi and soabi.startswith("pypy-"):
        # we want something like pypy36-pp73
        abi = "-".join(soabi.split("-")[:2])
        abi = abi.replace(".", "_").replace("-", "_")
    elif soabi:
        abi = soabi.replace(".", "_").replace("-", "_")
    else:
        abi = None

    return abi


def safer_name(name):
    return safe_name(name).replace("-", "_")


def safer_version(version):
    return safe_version(version).replace("-", "_")


def remove_readonly(func, path, excinfo):
    print(str(excinfo[1]))
    os.chmod(path, stat.S_IWRITE)
    func(path)


class bdist_wheel(Command):

    description = "create a wheel distribution"

    supported_compressions = OrderedDict(
        [("stored", ZIP_STORED), ("deflated", ZIP_DEFLATED)]
    )

    user_options = [
        ("bdist-dir=", "b", "temporary directory for creating the distribution"),
        (
            "plat-name=",
            "p",
            "platform name to embed in generated filenames "
            "(default: %s)" % get_platform(None),
        ),
        (
            "keep-temp",
            "k",
            "keep the pseudo-installation tree around after "
            + "creating the distribution archive",
        ),
        ("dist-dir=", "d", "directory to put final built distributions in"),
        ("skip-build", None, "skip rebuilding everything (for testing/debugging)"),
        (
            "relative",
            None,
            "build the archive using relative paths " "(default: false)",
        ),
        (
            "owner=",
            "u",
            "Owner name used when creating a tar file" " [default: current user]",
        ),
        (
            "group=",
            "g",
            "Group name used when creating a tar file" " [default: current group]",
        ),
        ("universal", None, "make a universal wheel" " (default: false)"),
        (
            "compression=",
            None,
            "zipfile compression (one of: {})"
            " (default: 'deflated')".format(", ".join(supported_compressions)),
        ),
        (
            "python-tag=",
            None,
            "Python implementation compatibility tag"
            " (default: '%s')" % (python_tag()),
        ),
        (
            "build-number=",
            None,
            "Build number for this particular version. "
            "As specified in PEP-0427, this must start with a digit. "
            "[default: None]",
        ),
        (
            "py-limited-api=",
            None,
            "Python tag (cp32|cp33|cpNN) for abi3 wheel tag" " (default: false)",
        ),
    ]

    boolean_options = ["keep-temp", "skip-build", "relative", "universal"]

    def initialize_options(self):
        self.bdist_dir = None
        self.data_dir = None
        self.plat_name = None
        self.plat_tag = None
        self.format = "zip"
        self.keep_temp = False
        self.dist_dir = None
        self.egginfo_dir = None
        self.root_is_pure = None
        self.skip_build = None
        self.relative = False
        self.owner = None
        self.group = None
        self.universal = False
        self.compression = "deflated"
        self.python_tag = python_tag()
        self.build_number = None
        self.py_limited_api = False
        self.plat_name_supplied = False

    def finalize_options(self):
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command("bdist").bdist_base
            self.bdist_dir = os.path.join(bdist_base, "wheel")

        self.data_dir = self.wheel_dist_name + ".data"
        self.plat_name_supplied = self.plat_name is not None

        try:
            self.compression = self.supported_compressions[self.compression]
        except KeyError:
            raise ValueError(f"Unsupported compression: {self.compression}")

        need_options = ("dist_dir", "plat_name", "skip_build")

        self.set_undefined_options("bdist", *zip(need_options, need_options))

        self.root_is_pure = not (
            self.distribution.has_ext_modules() or self.distribution.has_c_libraries()
        )

        if self.py_limited_api and not re.match(
            PY_LIMITED_API_PATTERN, self.py_limited_api
        ):
            raise ValueError("py-limited-api must match '%s'" % PY_LIMITED_API_PATTERN)

        # Support legacy [wheel] section for setting universal
        wheel = self.distribution.get_option_dict("wheel")
        if "universal" in wheel:
            # please don't define this in your global configs
            log.warning(
                "The [wheel] section is deprecated. Use [bdist_wheel] instead.",
            )
            val = wheel["universal"][1].strip()
            if val.lower() in ("1", "true", "yes"):
                self.universal = True

        if self.build_number is not None and not self.build_number[:1].isdigit():
            raise ValueError("Build tag (build-number) must start with a digit.")

    @property
    def wheel_dist_name(self):
        """Return distribution full name with - replaced with _"""
        components = (
            safer_name(self.distribution.get_name()),
            safer_version(self.distribution.get_version()),
        )
        if self.build_number:
            components += (self.build_number,)
        return "-".join(components)

    def get_tag(self):
        # bdist sets self.plat_name if unset, we should only use it for purepy
        # wheels if the user supplied it.
        if self.plat_name_supplied:
            plat_name = self.plat_name
        elif self.root_is_pure:
            plat_name = "any"
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

            if (
                plat_name in ("linux-x86_64", "linux_x86_64")
                and sys.maxsize == 2147483647
            ):
                plat_name = "linux_i686"

        plat_name = plat_name.lower().replace("-", "_").replace(".", "_")

        if self.root_is_pure:
            if self.universal:
                impl = "py2.py3"
            else:
                impl = self.python_tag
            tag = (impl, "none", plat_name)
        else:
            impl_name = tags.interpreter_name()
            impl_ver = tags.interpreter_version()
            impl = impl_name + impl_ver
            # We don't work on CPython 3.1, 3.0.
            if self.py_limited_api and (impl_name + impl_ver).startswith("cp3"):
                impl = self.py_limited_api
                abi_tag = "abi3"
            else:
                abi_tag = str(get_abi_tag()).lower()
            tag = (impl, abi_tag, plat_name)
            # issue gh-374: allow overriding plat_name
            supported_tags = [
                (t.interpreter, t.abi, plat_name) for t in tags.sys_tags()
            ]
            assert (
                tag in supported_tags
            ), f"would build wheel with unsupported tag {tag}"
        return tag

    def run(self):
        build_scripts = self.reinitialize_command("build_scripts")
        build_scripts.executable = "python"
        build_scripts.force = True

        build_ext = self.reinitialize_command("build_ext")
        build_ext.inplace = False

        if not self.skip_build:
            self.run_command("build")

        install = self.reinitialize_command("install", reinit_subcommands=True)
        install.root = self.bdist_dir
        install.compile = False
        install.skip_build = self.skip_build
        install.warn_dir = False

        # A wheel without setuptools scripts is more cross-platform.
        # Use the (undocumented) `no_ep` option to setuptools'
        # install_scripts command to avoid creating entry point scripts.
        install_scripts = self.reinitialize_command("install_scripts")
        install_scripts.no_ep = True

        # Use a custom scheme for the archive, because we have to decide
        # at installation time which scheme to use.
        for key in ("headers", "scripts", "data", "purelib", "platlib"):
            setattr(install, "install_" + key, os.path.join(self.data_dir, key))

        basedir_observed = ""

        if os.name == "nt":
            # win32 barfs if any of these are ''; could be '.'?
            # (distutils.command.install:change_roots bug)
            basedir_observed = os.path.normpath(os.path.join(self.data_dir, ".."))
            self.install_libbase = self.install_lib = basedir_observed

        setattr(
            install,
            "install_purelib" if self.root_is_pure else "install_platlib",
            basedir_observed,
        )

        log.info(f"installing to {self.bdist_dir}")

        self.run_command("install")

        impl_tag, abi_tag, plat_tag = self.get_tag()
        archive_basename = f"{self.wheel_dist_name}-{impl_tag}-{abi_tag}-{plat_tag}"
        if not self.relative:
            archive_root = self.bdist_dir
        else:
            archive_root = os.path.join(
                self.bdist_dir, self._ensure_relative(install.install_base)
            )

        self.set_undefined_options("install_egg_info", ("target", "egginfo_dir"))
        distinfo_dirname = "{}-{}.dist-info".format(
            safer_name(self.distribution.get_name()),
            safer_version(self.distribution.get_version()),
        )
        distinfo_dir = os.path.join(self.bdist_dir, distinfo_dirname)
        self.egg2dist(self.egginfo_dir, distinfo_dir)

        self.write_wheelfile(distinfo_dir)

        # Make the archive
        if not os.path.exists(self.dist_dir):
            os.makedirs(self.dist_dir)

        wheel_path = os.path.join(self.dist_dir, archive_basename + ".whl")
        with WheelFile(wheel_path, "w", self.compression) as wf:
            wf.write_files(archive_root)

        # Add to 'Distribution.dist_files' so that the "upload" command works
        getattr(self.distribution, "dist_files", []).append(
            (
                "bdist_wheel",
                "{}.{}".format(*sys.version_info[:2]),  # like 3.7
                wheel_path,
            )
        )

        if not self.keep_temp:
            log.info(f"removing {self.bdist_dir}")
            if not self.dry_run:
                rmtree(self.bdist_dir, onerror=remove_readonly)

    def write_wheelfile(
        self, wheelfile_base, generator="bdist_wheel (" + wheel_version + ")"
    ):
        from email.message import Message

        msg = Message()
        msg["Wheel-Version"] = "1.0"  # of the spec
        msg["Generator"] = generator
        msg["Root-Is-Purelib"] = str(self.root_is_pure).lower()
        if self.build_number is not None:
            msg["Build"] = self.build_number

        # Doesn't work for bdist_wininst
        impl_tag, abi_tag, plat_tag = self.get_tag()
        for impl in impl_tag.split("."):
            for abi in abi_tag.split("."):
                for plat in plat_tag.split("."):
                    msg["Tag"] = "-".join((impl, abi, plat))

        wheelfile_path = os.path.join(wheelfile_base, "WHEEL")
        log.info(f"creating {wheelfile_path}")
        buffer = BytesIO()
        BytesGenerator(buffer, maxheaderlen=0).flatten(msg)
        with open(wheelfile_path, "wb") as f:
            f.write(buffer.getvalue().replace(b"\r\n", b"\r"))

    def _ensure_relative(self, path):
        # copied from dir_util, deleted
        drive, path = os.path.splitdrive(path)
        if path[0:1] == os.sep:
            path = drive + path[1:]
        return path

    @property
    def license_paths(self):
        if setuptools_major_version >= 57:
            # Setuptools has resolved any patterns to actual file names
            return self.distribution.metadata.license_files or ()

        files = set()
        metadata = self.distribution.get_option_dict("metadata")
        if setuptools_major_version >= 42:
            # Setuptools recognizes the license_files option but does not do globbing
            patterns = self.distribution.metadata.license_files
        else:
            # Prior to those, wheel is entirely responsible for handling license files
            if "license_files" in metadata:
                patterns = metadata["license_files"][1].split()
            else:
                patterns = ()

        if "license_file" in metadata:
            warnings.warn(
                'The "license_file" option is deprecated. Use "license_files" instead.',
                DeprecationWarning,
            )
            files.add(metadata["license_file"][1])

        if not files and not patterns and not isinstance(patterns, list):
            patterns = ("LICEN[CS]E*", "COPYING*", "NOTICE*", "AUTHORS*")

        for pattern in patterns:
            for path in iglob(pattern):
                if path.endswith("~"):
                    log.debug(
                        f'ignoring license file "{path}" as it looks like a backup'
                    )
                    continue

                if path not in files and os.path.isfile(path):
                    log.info(
                        f'adding license file "{path}" (matched pattern "{pattern}")'
                    )
                    files.add(path)

        return files

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

            pat = os.path.join(os.path.dirname(egginfo_path), "*.egg-info")
            possible = glob.glob(pat)
            err = f"Egg metadata expected at {egginfo_path} but not found"
            if possible:
                alt = os.path.basename(possible[0])
                err += f" ({alt} found - possible misnamed archive file?)"

            raise ValueError(err)

        if os.path.isfile(egginfo_path):
            # .egg-info is a single file
            pkginfo_path = egginfo_path
            pkg_info = pkginfo_to_metadata(egginfo_path, egginfo_path)
            os.mkdir(distinfo_path)
        else:
            # .egg-info is a directory
            pkginfo_path = os.path.join(egginfo_path, "PKG-INFO")
            pkg_info = pkginfo_to_metadata(egginfo_path, pkginfo_path)

            # ignore common egg metadata that is useless to wheel
            shutil.copytree(
                egginfo_path,
                distinfo_path,
                ignore=lambda x, y: {
                    "PKG-INFO",
                    "requires.txt",
                    "SOURCES.txt",
                    "not-zip-safe",
                },
            )

            # delete dependency_links if it is only whitespace
            dependency_links_path = os.path.join(distinfo_path, "dependency_links.txt")
            with open(dependency_links_path) as dependency_links_file:
                dependency_links = dependency_links_file.read().strip()
            if not dependency_links:
                adios(dependency_links_path)

        pkg_info_path = os.path.join(distinfo_path, "METADATA")
        with open(pkg_info_path, "w", encoding="utf-8") as out:
            Generator(out, mangle_from_=False, maxheaderlen=0).flatten(pkg_info)

        for license_path in self.license_paths:
            filename = os.path.basename(license_path)
            shutil.copy(license_path, os.path.join(distinfo_path, filename))

        adios(egginfo_path)
