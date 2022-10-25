from __future__ import annotations

from pathlib import Path

from wheel._cli.unpack import unpack


def test_unpack(wheel_paths: list[Path], tmp_path: Path) -> None:
    """
    Make sure 'wheel unpack' works.
    This also verifies the integrity of our testing wheel files.
    """
    for wheel_path in wheel_paths:
        unpack(wheel_path, tmp_path)
