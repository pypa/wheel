from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

__version__ = "0.47.0"


def unpack(path: str | Path, dest: str | Path = ".") -> None:
    """Unpack a wheel.

    .. deprecated:: 0.45.0
        Use ``python -m wheel unpack`` instead.

    Parameters
    ----------
    path:
        Path to the wheel file.
    dest:
        Destination directory.
    """
    import warnings

    warnings.warn(
        "wheel.unpack is deprecated, use python -m wheel unpack instead",
        DeprecationWarning,
        stacklevel=2,
    )
    from wheel._commands.unpack import unpack as _unpack

    _unpack(str(path), str(dest))


def pack(directory: str | Path, dest_dir: str | Path = ".", build_number: str | None = None) -> None:
    """Pack a wheel.

    .. deprecated:: 0.45.0
        Use ``python -m wheel pack`` instead.

    Parameters
    ----------
    directory:
        Root directory of the unpacked wheel.
    dest_dir:
        Directory to store the wheel.
    build_number:
        Build tag to use in the wheel name.
    """
    import warnings

    warnings.warn(
        "wheel.pack is deprecated, use python -m wheel pack instead",
        DeprecationWarning,
        stacklevel=2,
    )
    from wheel._commands.pack import pack as _pack

    _pack(str(directory), str(dest_dir), build_number)
