"""
pytest local configuration plug-in
"""

from __future__ import annotations

import os.path
import subprocess
import sys
from pathlib import Path

import pytest
from pytest import TempPathFactory


@pytest.fixture(scope="session")
def wheels_and_eggs(tmp_path_factory: TempPathFactory) -> list[Path]:
    """Build wheels and eggs from test distributions."""
    test_distributions = [
        "complex-dist",
        "simple.dist",
        "headers.dist",
        "commasinfilenames.dist",
        "unicode.dist",
    ]

    if sys.platform != "win32":
        # ABI3 extensions don't really work on Windows
        test_distributions.append("abi3extension.dist")

    this_dir = Path(__file__).parent
    build_dir = tmp_path_factory.mktemp("build")
    dist_dir = tmp_path_factory.mktemp("dist")
    for dist in test_distributions:
        os.chdir(os.path.join(this_dir, "testdata", dist))
        subprocess.check_call(
            [
                sys.executable,
                "setup.py",
                "bdist_egg",
                "-b",
                str(build_dir),
                "-d",
                str(dist_dir),
                "bdist_wheel",
                "-b",
                str(build_dir),
                "-d",
                str(dist_dir),
            ]
        )

    return sorted(
        path for path in dist_dir.iterdir() if path.suffix in (".whl", ".egg")
    )


@pytest.fixture(scope="session")
def wheel_paths(wheels_and_eggs: list[Path]) -> list[Path]:
    return [path for path in wheels_and_eggs if path.suffix == ".whl"]


@pytest.fixture(scope="session")
def egg_paths(wheels_and_eggs: list[Path]) -> list[Path]:
    return [path for path in wheels_and_eggs if path.suffix == ".egg"]
