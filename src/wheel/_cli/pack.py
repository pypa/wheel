from __future__ import annotations

import re
from os import PathLike
from pathlib import Path

from .. import WheelWriter, make_filename
from . import WheelError

DIST_INFO_RE = re.compile(r"^(?P<namever>(?P<name>[^-]+)-(?P<ver>\d.*?))\.dist-info$")
BUILD_NUM_RE = re.compile(rb"Build: (\d\w*)$")


def pack(
    directory: str | PathLike[str],
    dest_dir: str | PathLike[str],
    build_number: str | None = None,
) -> None:
    """Repack a previously unpacked wheel directory into a new wheel file.

    The .dist-info/WHEEL file must contain one or more tags so that the target
    wheel file name can be determined.

    :param directory: The unpacked wheel directory
    :param dest_dir: Destination directory (defaults to the current directory)
    :param build_number: Build tag to use, if any

    """
    # Find the .dist-info directory
    directory = Path(directory)
    dist_info_dirs = [
        path
        for path in directory.iterdir()
        if path.is_dir() and DIST_INFO_RE.match(path.name)
    ]
    if len(dist_info_dirs) > 1:
        raise WheelError(f"Multiple .dist-info directories found in {directory}")
    elif not dist_info_dirs:
        raise WheelError(f"No .dist-info directories found in {directory}")

    # Determine the target wheel filename
    dist_info_dir = dist_info_dirs[0]
    match = DIST_INFO_RE.match(dist_info_dir.name)
    assert match
    name, version = match.groups()[1:]

    # Read the tags and the existing build number from .dist-info/WHEEL
    existing_build_number = None
    wheel_file_path = dist_info_dir / "WHEEL"
    with wheel_file_path.open() as f:
        tags = []
        for line in f:
            if line.startswith("Tag: "):
                tags.append(line.split(" ")[1].rstrip())
            elif line.startswith("Build: "):
                existing_build_number = line.split(" ")[1].rstrip()

        if not tags:
            raise WheelError(
                "No tags present in {}/WHEEL; cannot determine target wheel "
                "filename".format(dist_info_dir)
            )

    # Set the wheel file name and add/replace/remove the Build tag in .dist-info/WHEEL
    build_number = build_number if build_number is not None else existing_build_number
    if build_number is not None and build_number != existing_build_number:
        replacement = (
            f"Build: {build_number}\r\n".encode("ascii") if build_number else b""
        )
        with wheel_file_path.open("rb+") as f:
            wheel_file_content = f.read()
            if not BUILD_NUM_RE.subn(replacement, wheel_file_content)[1]:
                wheel_file_content += replacement

            f.seek(0)
            f.truncate()
            f.write(wheel_file_content)

    # Reassemble the tags for the wheel file
    impls = sorted({tag.split("-")[0] for tag in tags})
    abivers = sorted({tag.split("-")[1] for tag in tags})
    platforms = sorted({tag.split("-")[2] for tag in tags})

    # Repack the wheel
    filename = make_filename(
        name,
        version,
        build_number,
        ".".join(impls),
        ".".join(abivers),
        ".".join(platforms),
    )
    wheel_path = Path(dest_dir) / filename
    with WheelWriter(wheel_path) as wf:
        print(f"Repacking wheel as {wheel_path}...", end="", flush=True)
        wf.write_files_from_directory(directory)

    print("OK")
