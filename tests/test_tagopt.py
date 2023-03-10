"""
Tests for the bdist_wheel tag options (--python-tag, --universal, and
--plat-name)
"""

from __future__ import annotations

import subprocess
import sys

import pytest

SETUP_PY = """\
from setuptools import setup, Extension

setup(
    name="Test",
    version="1.0",
    author_email="author@example.com",
    py_modules=["test"],
    {ext_modules}
)
"""

EXT_MODULES = "ext_modules=[Extension('_test', sources=['test.c'])],"


@pytest.fixture
def temp_pkg(request, tmp_path):
    tmp_path.joinpath("test.py").write_text('print("Hello, world")', encoding="utf-8")

    ext = getattr(request, "param", [False, ""])
    if ext[0]:
        # if ext[1] is not '', it will write a bad header and fail to compile
        tmp_path.joinpath("test.c").write_text(
            "#include <std%sio.h>" % ext[1], encoding="utf-8"
        )
        setup_py = SETUP_PY.format(ext_modules=EXT_MODULES)
    else:
        setup_py = SETUP_PY.format(ext_modules="")

    tmp_path.joinpath("setup.py").write_text(setup_py, encoding="utf-8")
    if ext[0]:
        try:
            subprocess.check_call(
                [sys.executable, "setup.py", "build_ext"], cwd=str(tmp_path)
            )
        except subprocess.CalledProcessError:
            pytest.skip("Cannot compile C extensions")
    return tmp_path


@pytest.mark.parametrize("temp_pkg", [[True, "xxx"]], indirect=["temp_pkg"])
def test_nocompile_skips(temp_pkg):
    assert False  # noqa: B011 - should have skipped with a "Cannot compile" message


def test_default_tag(temp_pkg):
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel"], cwd=str(temp_pkg)
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name == f"Test-1.0-py{sys.version_info[0]}-none-any.whl"
    assert wheels[0].suffix == ".whl"


def test_build_number(temp_pkg):
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "--build-number=1"],
        cwd=str(temp_pkg),
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name == f"Test-1.0-1-py{sys.version_info[0]}-none-any.whl"
    assert wheels[0].suffix == ".whl"


def test_explicit_tag(temp_pkg):
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "--python-tag=py32"],
        cwd=str(temp_pkg),
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.startswith("Test-1.0-py32-")
    assert wheels[0].suffix == ".whl"


def test_universal_tag(temp_pkg):
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "--universal"], cwd=str(temp_pkg)
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.startswith("Test-1.0-py2.py3-")
    assert wheels[0].suffix == ".whl"


def test_universal_beats_explicit_tag(temp_pkg):
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "--universal", "--python-tag=py32"],
        cwd=str(temp_pkg),
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.startswith("Test-1.0-py2.py3-")
    assert wheels[0].suffix == ".whl"


def test_universal_in_setup_cfg(temp_pkg):
    temp_pkg.joinpath("setup.cfg").write_text(
        "[bdist_wheel]\nuniversal=1", encoding="utf-8"
    )
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel"], cwd=str(temp_pkg)
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.startswith("Test-1.0-py2.py3-")
    assert wheels[0].suffix == ".whl"


def test_pythontag_in_setup_cfg(temp_pkg):
    temp_pkg.joinpath("setup.cfg").write_text(
        "[bdist_wheel]\npython_tag=py32", encoding="utf-8"
    )
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel"], cwd=str(temp_pkg)
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.startswith("Test-1.0-py32-")
    assert wheels[0].suffix == ".whl"


def test_legacy_wheel_section_in_setup_cfg(temp_pkg):
    temp_pkg.joinpath("setup.cfg").write_text("[wheel]\nuniversal=1", encoding="utf-8")
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel"], cwd=str(temp_pkg)
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.startswith("Test-1.0-py2.py3-")
    assert wheels[0].suffix == ".whl"


def test_plat_name_purepy(temp_pkg):
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "--plat-name=testplat.pure"],
        cwd=str(temp_pkg),
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.endswith("-testplat_pure.whl")
    assert wheels[0].suffix == ".whl"


@pytest.mark.parametrize("temp_pkg", [[True, ""]], indirect=["temp_pkg"])
def test_plat_name_ext(temp_pkg):
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel", "--plat-name=testplat.arch"],
        cwd=str(temp_pkg),
    )

    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.endswith("-testplat_arch.whl")
    assert wheels[0].suffix == ".whl"


def test_plat_name_purepy_in_setupcfg(temp_pkg):
    temp_pkg.joinpath("setup.cfg").write_text(
        "[bdist_wheel]\nplat_name=testplat.pure", encoding="utf-8"
    )
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel"], cwd=str(temp_pkg)
    )
    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.endswith("-testplat_pure.whl")
    assert wheels[0].suffix == ".whl"


@pytest.mark.parametrize("temp_pkg", [[True, ""]], indirect=["temp_pkg"])
def test_plat_name_ext_in_setupcfg(temp_pkg):
    temp_pkg.joinpath("setup.cfg").write_text(
        "[bdist_wheel]\nplat_name=testplat.arch", encoding="utf-8"
    )
    subprocess.check_call(
        [sys.executable, "setup.py", "bdist_wheel"], cwd=str(temp_pkg)
    )

    dist_dir = temp_pkg.joinpath("dist")
    assert dist_dir.is_dir()
    wheels = list(dist_dir.iterdir())
    assert len(wheels) == 1
    assert wheels[0].name.endswith("-testplat_arch.whl")
    assert wheels[0].suffix == ".whl"
