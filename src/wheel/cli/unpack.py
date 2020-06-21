import sys
from pathlib import Path
from typing import Union

from ..wheelfile import WheelFile

if sys.version_info >= (3, 6):
    from os import PathLike
else:
    from pathlib import Path as PathLike


def unpack(path: Union[str, PathLike], dest: Union[str, PathLike] = '.') -> None:
    """Unpack a wheel.

    Wheel content will be unpacked to {dest}/{name}-{ver}, where {name}
    is the package name and {ver} its version.

    :param path: The path to the wheel.
    :param dest: Destination directory (default to current directory).
    """
    with WheelFile(path) as wf:
        namever = wf.metadata.name + '.' + wf.metadata.version
        destination = Path(dest) / namever
        destination.mkdir(exist_ok=True)
        print("Unpacking to: {}...".format(destination), end='')
        sys.stdout.flush()
        wf.unpack(destination)

    print('OK')
