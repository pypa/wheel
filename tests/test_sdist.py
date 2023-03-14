import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

pytest.importorskip("flit")
pytest.importorskip("build")

# This test must be run from the source directory - okay to skip if not
DIR = Path(__file__).parent.resolve()
MAIN_DIR = DIR.parent


def test_compare_sdists(monkeypatch, tmp_path):
    monkeypatch.chdir(MAIN_DIR)

    sdist_build_dir = tmp_path / "bdir"

    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--sdist",
            "--no-isolation",
            f"--outdir={sdist_build_dir}",
        ],
        check=True,
    )

    (sdist_build,) = sdist_build_dir.glob("*.tar.gz")

    # Flit doesn't allow targeting directories, as far as I can tell
    process = subprocess.run(
        [sys.executable, "-m", "flit", "build", "--format=sdist"],
        stderr=subprocess.PIPE,
    )
    if process.returncode != 0:
        pytest.fail(process.stderr.decode("utf-8"))

    (sdist_flit,) = Path("dist").glob("*.tar.gz")

    out = [set(), set()]
    for i, sdist in enumerate([sdist_build, sdist_flit]):
        with tarfile.open(str(sdist), "r:gz") as tar:
            out[i] = set(tar.getnames())

    assert out[0] == (out[1] - {"setup.py"})
