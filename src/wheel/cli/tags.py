from __future__ import annotations

import itertools
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager

from ..wheelfile import WheelFile
from .pack import pack
from .unpack import unpack

try:
    from typing import Iterator
except ImportError:
    pass


@contextmanager
def redirect_stdout(new_target):
    old_target, sys.stdout = sys.stdout, new_target
    try:
        yield new_target
    finally:
        sys.stdout = old_target


@contextmanager
def temporary_directory():
    try:
        dirname = tempfile.mkdtemp()
        yield dirname
    finally:
        shutil.rmtree(dirname)


class InWheelCtx:
    @property
    def parsed_filename(self):
        return self.wheel.parsed_filename

    @property
    def filename(self):
        return self.wheel.filename

    def __init__(self, wheel, tmpdir):
        self.wheel = WheelFile(wheel)
        self.tmpdir = tmpdir
        self.build_number = None
        # If dirname is unset, don't pack a new wheel
        self.dirname = None

    def __enter__(self):
        with redirect_stdout(sys.stderr):
            unpack(self.wheel.filename, self.tmpdir)
        self.wheel.__enter__()
        return self

    def __exit__(self, *args):
        self.wheel.__exit__(*args)
        if self.dirname:
            with redirect_stdout(sys.stderr):
                pack(
                    os.path.join(
                        self.tmpdir, self.wheel.parsed_filename.group("namever")
                    ),
                    self.dirname,
                    self.build_number,
                )


def compute_tags(original_tags: list[str], new_tags: list[str] | None) -> list[str]:
    """Add or replace tags."""

    if not new_tags:
        return original_tags

    if new_tags[0] == "":
        return original_tags + new_tags[1:]
    else:
        return new_tags


def tags(
    wheels: list[str],
    python_tags: list[str] | None = None,
    abi_tags: list[str] | None = None,
    platform_tags: list[str] | None = None,
    build_number: int | None = None,
    remove: bool = False,
) -> Iterator[str]:
    """Change the tags on a wheel file.

    The tags are left unchanged if they are not specified. To specify "none",
    use ["none"]. To append to the previous tags, use ["", ...].

    :param wheels: The paths to the wheels.
    :param python_tags: The Python tags to set.
    :param abi_tags: The ABI tags to set.
    :param platform_tags: The platform tags to set.
    :param build_number: The build number to set.
    :param remove: Remove the original wheel.
    """

    for wheel in wheels:
        with temporary_directory() as tmpdir, InWheelCtx(wheel, tmpdir) as wfctx:
            namever = wfctx.parsed_filename.group("namever")
            build = wfctx.parsed_filename.group("build")
            original_python_tags = wfctx.parsed_filename.group("pyver").split(".")
            original_abi_tags = wfctx.parsed_filename.group("abi").split(".")
            orignial_plat_tags = wfctx.parsed_filename.group("plat").split(".")

            if build_number is not None:
                build = str(build_number)

            final_python_tags = compute_tags(original_python_tags, python_tags)
            final_abi_tags = compute_tags(original_abi_tags, abi_tags)
            final_plat_tags = compute_tags(orignial_plat_tags, platform_tags)

            final_tags = [
                ".".join(sorted(final_python_tags)),
                ".".join(sorted(final_abi_tags)),
                ".".join(sorted(final_plat_tags)),
            ]

            if build:
                final_tags.insert(0, build)
            final_tags.insert(0, namever)

            original_wheel_name = os.path.basename(wfctx.filename)
            final_wheel_name = "-".join(final_tags) + ".whl"

            if original_wheel_name != final_wheel_name:

                wheelinfo = os.path.join(
                    tmpdir, namever, wfctx.wheel.dist_info_path, "WHEEL"
                )
                with open(wheelinfo, "rb+") as f:
                    lines = [line for line in f if not line.startswith(b"Tag:")]
                    for a, b, c in itertools.product(
                        final_python_tags, final_abi_tags, final_plat_tags
                    ):
                        lines.append(f"Tag: {a}-{b}-{c}\r\n".encode("ascii"))
                    f.seek(0)
                    f.truncate()
                    f.write(b"".join(lines))

                wfctx.build_number = build
                wfctx.dirname = os.path.dirname(wheel)

        if remove:
            os.remove(wheel)

        yield final_wheel_name
