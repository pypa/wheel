from __future__ import annotations

import os.path
import re

from wheel.cli.convert import convert, egg_info_re
from wheel.wheelfile import WHEEL_INFO_RE


def test_egg_re():
    """Make sure egg_info_re matches."""
    egg_names_path = os.path.join(os.path.dirname(__file__), "eggnames.txt")
    with open(egg_names_path) as egg_names:
        for line in egg_names:
            line = line.strip()
            if line:
                assert egg_info_re.match(line), line


def test_convert_egg(egg_paths, tmpdir):
    convert(egg_paths, str(tmpdir), verbose=False)
    wheel_names = [path.basename for path in tmpdir.listdir()]
    assert len(wheel_names) == len(egg_paths)
    assert all(WHEEL_INFO_RE.match(filename) for filename in wheel_names)
    assert all(
        re.match(r"^[\w\d.]+-\d\.\d-\w+\d+-[\w\d]+-[\w\d]+\.whl$", fname)
        for fname in wheel_names
    )
