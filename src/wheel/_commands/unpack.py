from __future__ import annotations

import os
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
        # Read the current umask without changing it
        umask = os.umask(0)
        os.umask(umask)
        for zinfo in wf.filelist:
            target_path = Path(wf.extract(zinfo, destination))
            if target_path.resolve() == unpack_root:
                # Security: don't change the permissions of the unpack root
                continue

            # Set permissions to the same values as they were set in the archive
            # We have to do this manually due to
            # https://github.com/python/cpython/issues/59999
            # Security: apply the umask so that the archive cannot make the
            # extracted files writable by other users
            permissions = zinfo.external_attr >> 16 & 0o777 & ~umask
            target_path.chmod(permissions)

    print("OK")
