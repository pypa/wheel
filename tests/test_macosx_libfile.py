from __future__ import annotations

from pathlib import Path

import pytest

from wheel import macosx_libfile
from wheel.macosx_libfile import calculate_macosx_platform_tag


@pytest.mark.parametrize(
    ("dylib_count", "expected_form"),
    [
        pytest.param(1, "this file", id="single"),
        pytest.param(2, "these files", id="multiple"),
    ],
)
def test_calculate_macosx_platform_tag_files_form(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    dylib_count: int,
    expected_form: str,
) -> None:
    for index in range(dylib_count):
        tmp_path.joinpath(f"lib{index}.dylib").write_bytes(b"")

    monkeypatch.setattr(
        macosx_libfile,
        "extract_macosx_min_system_version",
        lambda path: (11, 0, 0),
    )

    tag = calculate_macosx_platform_tag(str(tmp_path), "macosx-10.9-x86_64")

    assert tag == "macosx_11_0_x86_64"
    warning = capsys.readouterr().err
    assert expected_form in warning
