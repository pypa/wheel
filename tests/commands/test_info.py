from __future__ import annotations

import base64
import hashlib
import os
import shutil
import sys
import zipfile
from io import StringIO
from unittest.mock import patch

import pytest

from wheel._commands.info import info

from .util import run_command

THISDIR = os.path.dirname(__file__)
TESTWHEEL_NAME = "test-1.0-py2.py3-none-any.whl"
TESTWHEEL_PATH = os.path.join(THISDIR, "..", "testdata", TESTWHEEL_NAME)


def _build_wheel_with_modified_metadata(
    src_whl: str, dest_dir: os.PathLike[str], wheel_content: str
) -> str:
    """Copy a wheel and replace its WHEEL metadata, updating the RECORD hash.

    Returns the path to the new wheel file.
    """
    dest_whl = os.path.join(dest_dir, os.path.basename(src_whl))
    shutil.copy2(src_whl, dest_whl)

    with zipfile.ZipFile(dest_whl, "r") as zr:
        wheel_path = record_path = None
        for name in zr.namelist():
            if name.endswith("/WHEEL"):
                wheel_path = name
            elif name.endswith("/RECORD"):
                record_path = name
        assert wheel_path is not None
        assert record_path is not None
        original_record = zr.read(record_path).decode()

    modified_bytes = wheel_content.encode()

    # Compute new hash and size for the WHEEL file
    digest = hashlib.sha256(modified_bytes).digest()
    hash_str = "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    size_str = str(len(modified_bytes))

    # Update the RECORD with the new hash for the WHEEL file
    new_record_lines = []
    for line in original_record.splitlines():
        if line.startswith(wheel_path):
            new_record_lines.append(f"{wheel_path},{hash_str},{size_str}")
        else:
            new_record_lines.append(line)
    modified_record = "\n".join(new_record_lines) + "\n"

    # Rewrite the wheel with the modified WHEEL file and updated RECORD
    tmp_whl = os.path.join(dest_dir, "tmp.whl")
    with zipfile.ZipFile(dest_whl, "r") as zr, zipfile.ZipFile(tmp_whl, "w") as zw:
        for item in zr.infolist():
            if item.filename == wheel_path:
                zw.writestr(item, modified_bytes)
            elif item.filename == record_path:
                zw.writestr(item, modified_record.encode())
            else:
                zw.writestr(item, zr.read(item.filename))

    os.replace(tmp_whl, dest_whl)
    return dest_whl


def _capture_info_output(wheel_path: str, verbose: bool = False) -> str:
    """Run info() and capture its stdout."""
    stdout = StringIO()
    with patch.object(sys, "stdout", stdout):
        info(wheel_path, verbose=verbose)
    return stdout.getvalue()


def test_info_basic() -> None:
    """Test basic wheel info display."""
    output = run_command("info", TESTWHEEL_PATH)

    # Check basic package information is displayed
    assert "Name: test" in output
    assert "Version: 1.0" in output
    assert "Wheel-Version: 1.0" in output
    assert "Root-Is-Purelib: false" in output

    # Check tags are displayed
    assert "Tags:" in output
    assert "py2-none-any" in output
    assert "py3-none-any" in output

    # Check metadata is displayed
    assert "Summary: Test module" in output
    assert "Author: Paul Moore" in output
    assert "Author-email: test@example.com" in output
    assert "Home-page: http://test.example.com/" in output
    assert "License: MIT License" in output

    # Check file information
    assert "Files: 14" in output
    assert "Size: 8,114 bytes" in output


def test_info_generator() -> None:
    """Test that a single Generator value is displayed."""
    output = run_command("info", TESTWHEEL_PATH)
    assert "Generator: bdist_wheel (0.30.0)" in output


def test_info_multiple_generators(tmp_path: os.PathLike[str]) -> None:
    """Test that multiple Generator values are each displayed on their own line."""
    wheel_content = (
        "Wheel-Version: 1.0\n"
        "Generator: bdist_wheel (0.30.0)\n"
        "Generator: auditwheel (6.0.0)\n"
        "Root-Is-Purelib: false\n"
        "Tag: py2-none-any\n"
        "Tag: py3-none-any\n"
    )
    whl = _build_wheel_with_modified_metadata(TESTWHEEL_PATH, str(tmp_path), wheel_content)
    output = _capture_info_output(whl)

    assert "Generator: bdist_wheel (0.30.0)" in output
    assert "Generator: auditwheel (6.0.0)" in output
    # Ensure exactly two Generator lines are printed
    assert output.count("Generator:") == 2


def test_info_no_generator(tmp_path: os.PathLike[str]) -> None:
    """Test that missing Generator values produce no Generator lines."""
    wheel_content = (
        "Wheel-Version: 1.0\n"
        "Root-Is-Purelib: false\n"
        "Tag: py2-none-any\n"
        "Tag: py3-none-any\n"
    )
    whl = _build_wheel_with_modified_metadata(TESTWHEEL_PATH, str(tmp_path), wheel_content)
    output = _capture_info_output(whl)

    assert "Generator" not in output


def test_info_verbose() -> None:
    """Test verbose wheel info display with file listing."""
    output = run_command("info", "--verbose", TESTWHEEL_PATH)

    # Check that basic info is still there
    assert "Name: test" in output
    assert "Version: 1.0" in output

    # Check that file listing is included
    assert "File listing:" in output
    assert "hello/hello.py" in output
    assert "hello.pyd" in output
    assert "test-1.0.dist-info/METADATA" in output
    assert "test-1.0.dist-info/WHEEL" in output
    assert "test-1.0.dist-info/RECORD" in output

    # Check file sizes are displayed
    assert "6,656 bytes" in output  # hello.pyd
    assert "42 bytes" in output  # hello.py


def test_info_nonexistent_file() -> None:
    """Test info command with non-existent wheel file."""
    from wheel._commands.info import info

    with pytest.raises(
        FileNotFoundError, match="Wheel file not found: nonexistent.whl"
    ):
        info("nonexistent.whl")


def test_info_help() -> None:
    """Test info command help."""
    output = run_command("info", "--help")

    assert "info" in output
    assert "Wheel file to show information for" in output
    assert "wheelfile" in output
    assert "--verbose" in output


def test_info_short_verbose_flag() -> None:
    """Test that -v works as alias for --verbose."""
    output = run_command("info", "-v", TESTWHEEL_PATH)

    # Should include file listing like --verbose
    assert "File listing:" in output
    assert "hello/hello.py" in output
