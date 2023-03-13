from __future__ import annotations

import os
import stat
from pathlib import Path

from ..wheelfile import WheelFile


def unpack(path: str, dest: str = ".") -> None:
    """Unpack a wheel.

    Wheel content will be unpacked to {dest}/{name}-{ver}, where {name}
    is the package name and {ver} its version.

    :param path: The path to the wheel.
    :param dest: Destination directory (default to current directory).
    """
    umask = os.umask(0)
    os.umask(umask)
    with WheelFile(path) as wf:
        namever = wf.parsed_filename.group("namever")
        destination = Path(dest) / namever
        print(f"Unpacking to: {destination}...", end="", flush=True)
        for zinfo in wf.filelist:
            extracted_path = destination / zinfo.filename
            wf.extract(zinfo, extracted_path)

            # Set the executable bit if it was set in the archive
            if stat.S_IMODE(zinfo.external_attr >> 16 & 0o111):
                extracted_path.chmod(0o777 & ~umask | 0o111)

    print("OK")
