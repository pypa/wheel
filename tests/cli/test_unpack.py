from __future__ import annotations

from wheel.cli.unpack import unpack


def test_unpack(wheel_paths, tmpdir):
    """
    Make sure 'wheel unpack' works.
    This also verifies the integrity of our testing wheel files.
    """
    for wheel_path in wheel_paths:
        unpack(wheel_path, str(tmpdir))
