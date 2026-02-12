from __future__ import annotations

import os

import pytest

from .util import run_command

THISDIR = os.path.dirname(__file__)
TESTWHEEL_NAME = "test-1.0-py2.py3-none-any.whl"
TESTWHEEL_PATH = os.path.join(THISDIR, "..", "testdata", TESTWHEEL_NAME)


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

    with pytest.raises(FileNotFoundError, match="Wheel file not found: nonexistent.whl"):
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
