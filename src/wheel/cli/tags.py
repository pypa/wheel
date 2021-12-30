from __future__ import annotations

import itertools
import os

from ..wheelfile import WheelFile
from .pack import read_tags, set_build_number

try:
    from typing import Iterator
except ImportError:
    pass


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
        with WheelFile(wheel, "r") as f:
            wheel_info = f.read(f.dist_info_path + "/WHEEL")

            original_wheel_name = os.path.basename(f.filename)
            namever = f.parsed_filename.group("namever")
            build = f.parsed_filename.group("build")
            original_python_tags = f.parsed_filename.group("pyver").split(".")
            original_abi_tags = f.parsed_filename.group("abi").split(".")
            orignial_plat_tags = f.parsed_filename.group("plat").split(".")

        tags, existing_build_number = read_tags(wheel_info)

        impls = {tag.split("-")[0] for tag in tags}
        abivers = {tag.split("-")[1] for tag in tags}
        platforms = {tag.split("-")[2] for tag in tags}

        if impls != set(original_python_tags):
            raise AssertionError(f"{impls} != {original_python_tags}")

        if abivers != set(original_abi_tags):
            raise AssertionError(f"{abivers} != {original_abi_tags}")

        if platforms != set(orignial_plat_tags):
            raise AssertionError(f"{platforms} != {orignial_plat_tags}")

        if existing_build_number != build:
            raise AssertionError(
                f"Incorrect filename '{build}' & "
                f"*.dist-info/WHEEL '{existing_build_number}' build numbers"
            )

        # Start changing as needed
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

        final_wheel_name = "-".join(final_tags) + ".whl"

        if original_wheel_name != final_wheel_name:
            tags = [
                f"{a}-{b}-{c}"
                for a, b, c in itertools.product(
                    final_python_tags, final_abi_tags, final_plat_tags
                )
            ]

            original_wheel_path = os.path.join(
                os.path.dirname(f.filename), original_wheel_name
            )
            final_wheel_path = os.path.join(
                os.path.dirname(f.filename), final_wheel_name
            )

            with WheelFile(original_wheel_path, "r") as fin, WheelFile(
                final_wheel_path, "w"
            ) as fout:
                fout.comment = fin.comment  # preserve the comment
                for item in fin.infolist():
                    if item.filename == f.dist_info_path + "/RECORD":
                        continue
                    if item.filename == f.dist_info_path + "/WHEEL":
                        content = fin.read(item)
                        content = set_tags(content, tags)
                        content = set_build_number(content, build)
                        fout.writestr(item, content)
                    else:
                        fout.writestr(item, fin.read(item))

            if remove:
                os.remove(original_wheel_path)

        yield final_wheel_name


def set_tags(in_string: bytes, tags: list[str]) -> bytes:
    """Set the tags in the .dist-info/WHEEL file contents.

    :param in_string: The string to modify.
    :param tags: The tags to set.
    """

    lines = [line for line in in_string.splitlines() if not line.startswith(b"Tag:")]
    for tag in tags:
        lines.append(b"Tag: " + tag.encode("ascii"))
    in_string = b"\r\n".join(lines) + b"\r\n"

    return in_string
