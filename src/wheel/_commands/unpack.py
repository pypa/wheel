from __future__ import annotations

from pathlib import Path

from ..wheelfile import WheelFile


def unpack(path: str, dest: str = ".") -> None:
    """Unpack a wheel.

    Wheel content will be unpacked to {dest}/{name}-{ver}, where {name}
    is the package name and {ver} its version.

    :param path: The path to the wheel.
    :param dest: Destination directory (default to current directory).
    """
    with WheelFile(path) as wf:
        namever = wf.parsed_filename.group("namever")
        destination = Path(dest) / namever
        unpack_root = destination.resolve()
        print(f"Unpacking to: {destination}...", end="", flush=True)
        for zinfo in wf.filelist:
            target_path = Path(wf.extract(zinfo, destination))
            if target_path.resolve() == unpack_root:
                # Security: don't change the permissions of the unpack root
                continue

            # Set permissions to the same values as they were set in the archive
            # We have to do this manually due to
            # https://github.com/python/cpython/issues/59999
            permissions = zinfo.external_attr >> 16 & 0o777
            target_path.chmod(permissions)

    print("OK")
