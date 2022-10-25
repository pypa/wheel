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
from logging import getLogger
from pathlib import Path
from shutil import rmtree
from sysconfig import get_config_var

import pkg_resources
from setuptools import Command

from ._macosx_libfile import calculate_macosx_platform_tag
from ._metadata import pkginfo_to_metadata
from ._wheelfile import WheelWriter, make_filename
from .vendored.packaging import tags

safe_name = pkg_resources.safe_name
safe_version = pkg_resources.safe_version
logger = getLogger("wheel")

PY_LIMITED_API_PATTERN = r"cp3\d"


def python_tag() -> str:
    return f"py{sys.version_info[0]}"


def get_platform(archive_root: str | None) -> str:
    """Return our platform name 'win32', 'linux_x86_64'"""
    result = sysconfig.get_platform()
    if result.startswith("macosx") and archive_root is not None:
        result = calculate_macosx_platform_tag(archive_root, result)
    elif result == "linux-x86_64" and sys.maxsize == 2147483647:
        # pip pull request #3497
        result = "linux-i686"

    return result.replace("-", "_")


def get_flag(
    var: str, fallback: bool, expected: bool = True, warn: bool = True
) -> bool:
    """Use a fallback value for determining SOABI flags if the needed config
    var is unset or unavailable."""
    val = get_config_var(var)
    if val is None:
        if warn:
            warnings.warn(
                f"Config variable '{var}' is unset, Python ABI tag may " "be incorrect",
                RuntimeWarning,
                2,
            )

        return fallback

    return val == expected


def get_abi_tag() -> str | None:
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


def safer_name(name: str) -> str:
    return safe_name(name).replace("-", "_")


def safer_version(version: str) -> str:
    return safe_version(version).replace("-", "_")


def remove_readonly(func, path, excinfo) -> None:
    print(str(excinfo[1]))
    os.chmod(path, stat.S_IWRITE)
    func(path)


class bdist_wheel(Command):

    description = "create a wheel distribution"

    supported_compressions = ("stored", "deflated")

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

    def finalize_options(self) -> None:
        if self.bdist_dir is None:
            bdist_base = self.get_finalized_command(
                "bdist"
            ).bdist_base  # type: ignore[attr-defined]
            self.bdist_dir = os.path.join(bdist_base, "wheel")

        self.data_dir = self.wheel_dist_name + ".data"
        self.plat_name_supplied = self.plat_name is not None

        if self.compression not in self.supported_compressions:
            raise ValueError(f"Unsupported compression: {self.compression}")

        need_options = ("dist_dir", "plat_name", "skip_build")

        self.set_undefined_options("bdist", *zip(need_options, need_options))

        self.root_is_pure = not (
            self.distribution.has_ext_modules()  # type: ignore[attr-defined]
            or self.distribution.has_c_libraries()  # type: ignore[attr-defined]
        )

        if self.py_limited_api and not re.match(
            PY_LIMITED_API_PATTERN, self.py_limited_api
        ):
            raise ValueError(f"py-limited-api must match {PY_LIMITED_API_PATTERN!r}")

        # Support legacy [wheel] section for setting universal
        wheel = self.distribution.get_option_dict("wheel")  # type: ignore[attr-defined]
        if "universal" in wheel:
            # please don't define this in your global configs
            logger.warning(
                "The [wheel] section is deprecated. Use [bdist_wheel] instead.",
            )
            val = wheel["universal"][1].strip()
            if val.lower() in ("1", "true", "yes"):
                self.universal = True

        if self.build_number is not None and not self.build_number[:1].isdigit():
            raise ValueError("Build tag (build-number) must start with a digit.")

    @property
    def wheel_dist_name(self) -> str:
        """Return distribution full name with - replaced with _"""
        components: tuple[str, ...] = (
            safer_name(self.distribution.get_name()),  # type: ignore[attr-defined]
            safer_version(
                self.distribution.get_version()  # type: ignore[attr-defined]
            ),
        )
        if self.build_number:
            components += (self.build_number,)
        return "-".join(components)

    def get_tag(self) -> tuple[str, str, str]:
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

    def run(self) -> None:
        build_scripts = self.reinitialize_command("build_scripts")
        build_scripts.executable = "python"  # type: ignore[attr-defined]
        build_scripts.force = True  # type: ignore[attr-defined]

        build_ext = self.reinitialize_command("build_ext")
        build_ext.inplace = False  # type: ignore[attr-defined]

        if not self.skip_build:
            self.run_command("build")

        install = self.reinitialize_command("install", reinit_subcommands=True)
        install.root = self.bdist_dir  # type: ignore[attr-defined]
        install.compile = False  # type: ignore[attr-defined]
        install.skip_build = self.skip_build  # type: ignore[attr-defined]
        install.warn_dir = False  # type: ignore[attr-defined]

        # A wheel without setuptools scripts is more cross-platform.
        # Use the (undocumented) `no_ep` option to setuptools'
        # install_scripts command to avoid creating entry point scripts.
        install_scripts = self.reinitialize_command("install_scripts")
        install_scripts.no_ep = True  # type: ignore[attr-defined]

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

        logger.info("installing to %s", self.bdist_dir)
        self.run_command("install")

        impl_tag, abi_tag, plat_tag = self.get_tag()
        archive_basename = make_filename(
            self.distribution.get_name(),  # type: ignore[attr-defined]
            self.distribution.get_version(),  # type: ignore[attr-defined]
            self.build_number,
            impl_tag,
            abi_tag,
            plat_tag,
        )
        archive_root = Path(self.bdist_dir)
        if self.relative:
            archive_root /= self._ensure_relative(
                install.install_base  # type: ignore[attr-defined]
            )

        # Make the archive
        if not os.path.exists(self.dist_dir):
            os.makedirs(self.dist_dir)

        wheel_path = Path(self.dist_dir) / archive_basename
        logger.info("creating '%s' and adding '%s' to it", wheel_path, archive_root)
        with WheelWriter(
            wheel_path,
            compress=self.compression == "deflated",
            root_is_purelib=self.root_is_pure,
        ) as wf:
            deferred = []
            for root, dirnames, filenames in os.walk(archive_root):
                # Sort the directory names so that `os.walk` will walk them in a
                # defined order on the next iteration.
                dirnames.sort()
                root_path = Path(root)
                if root_path.name.endswith(".egg-info"):
                    continue

                for name in sorted(filenames):
                    path = root_path / name
                    if path.is_file():
                        archive_name = path.relative_to(archive_root).as_posix()
                        if root.endswith(".dist-info"):
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
                wf.write_distinfo_file(
                    os.path.basename(license_path), license_path.read_bytes()
                )

            # Write the metadata files from the .egg-info directory
            self.set_undefined_options("install_egg_info", ("target", "egginfo_dir"))
            for path in Path(self.egginfo_dir).iterdir():
                if path.name == "PKG-INFO":
                    items = pkginfo_to_metadata(path)
                    wf.write_metadata(items)
                elif path.name not in {
                    "requires.txt",
                    "SOURCES.txt",
                    "not-zip-safe",
                    "dependency_links.txt",
                }:
                    wf.write_distinfo_file(path.name, path.read_bytes())

        shutil.rmtree(self.egginfo_dir)

        # Add to 'Distribution.dist_files' so that the "upload" command works
        getattr(
            self.distribution, "dist_files", []  # type: ignore[attr-defined]
        ).append(
            (
                "bdist_wheel",
                "{}.{}".format(*sys.version_info[:2]),  # like 3.7
                str(wheel_path),
            )
        )

        if not self.keep_temp:
            logger.info(f"removing {self.bdist_dir}")
            if not self.dry_run:  # type: ignore[attr-defined]
                rmtree(self.bdist_dir, onerror=remove_readonly)

    def _ensure_relative(self, path: str) -> str:
        # copied from dir_util, deleted
        drive, path = os.path.splitdrive(path)
        if path[0:1] == os.sep:
            path = drive + path[1:]
        return path

    @property
    def license_paths(self) -> list[Path]:
        metadata = self.distribution.metadata  # type: ignore[attr-defined]
        files = sorted(metadata.license_files or [])
        return [Path(path) for path in files]
