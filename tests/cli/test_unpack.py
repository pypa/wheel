from __future__ import annotations

import platform
import stat

import pytest

from wheel.cli.unpack import unpack
from wheel.wheelfile import WheelFile


def test_unpack(wheel_paths, tmp_path):
    """
    Make sure 'wheel unpack' works.
    This also verifies the integrity of our testing wheel files.
    """
    for wheel_path in wheel_paths:
        unpack(wheel_path, str(tmp_path))


@pytest.mark.skipif(
    platform.system() == "Windows", reason="Windows does not support the executable bit"
)
def test_unpack_executable_bit(tmp_path):
    wheel_path = tmp_path / "test-1.0-py3-none-any.whl"
    script_path = tmp_path / "script"
    script_path.write_bytes(b"test script")
    script_path.chmod(0o755)
    with WheelFile(wheel_path, "w") as wf:
        wf.write(str(script_path), "nested/script")

    script_path.unlink()
    script_path = tmp_path / "test-1.0" / "nested" / "script"
    unpack(str(wheel_path), str(tmp_path))
    assert not script_path.is_dir()
    assert stat.S_IMODE(script_path.stat().st_mode) == 0o755
