from __future__ import annotations

import os.path
import re
from pathlib import Path

from wheel._cli.convert import convert, egg_info_re


def test_egg_re() -> None:
    """Make sure egg_info_re matches."""
    egg_names_path = os.path.join(os.path.dirname(__file__), "eggnames.txt")
    with open(egg_names_path) as egg_names:
        for line in egg_names:
            line = line.strip()
            if line:
                assert egg_info_re.match(line), line


def test_convert_egg(egg_paths: list[Path], tmp_path: Path) -> None:
    convert(egg_paths, tmp_path, verbose=False)
    wheel_names = [path.name for path in tmp_path.iterdir()]
    assert len(wheel_names) == len(egg_paths)
    for fname in wheel_names:
        assert re.match(r"^[\w\d.]+-\d\.\d-\w+\d+-[\w\d]+-[\w\d]+\.whl$", fname)
