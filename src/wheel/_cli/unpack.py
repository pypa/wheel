from __future__ import annotations

from os import PathLike
from pathlib import Path

from .. import WheelReader


def unpack(path: str | PathLike[str], dest: str | PathLike[str] = ".") -> None:
    """Unpack a wheel.

    Wheel content will be unpacked to {dest}/{name}-{ver}, where {name}
    is the package name and {ver} its version.

    :param path: The path to the wheel.
    :param dest: Destination directory (default to current directory).
    """
    with WheelReader(path) as wf:
        namever = f"{wf.name}.{wf.version}"
        destination = Path(dest) / namever
        destination.mkdir(exist_ok=True)
        print(f"Unpacking to: {destination}...", end="", flush=True)
        wf.extractall(destination)

    print("OK")
