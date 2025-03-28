from __future__ import annotations

import email.policy
import os
from email.message import Message
from email.parser import BytesParser
from zipfile import Path, ZipFile

import pytest
from pytest import TempPathFactory

from .util import run_command

THISDIR = os.path.dirname(__file__)
TESTWHEEL_NAME = "test-1.0-py2.py3-none-any.whl"
TESTWHEEL_PATH = os.path.join(THISDIR, "..", "testdata", TESTWHEEL_NAME)


@pytest.mark.filterwarnings("error:Duplicate name")
@pytest.mark.parametrize(
    "build_tag_arg, existing_build_tag, filename",
    [
        pytest.param(None, None, "test-1.0-py2.py3-none-any.whl", id="nobuildnum"),
        pytest.param("2b", None, "test-1.0-2b-py2.py3-none-any.whl", id="newbuildarg"),
        pytest.param(None, "3", "test-1.0-3-py2.py3-none-any.whl", id="oldbuildnum"),
        pytest.param("", "3", "test-1.0-py2.py3-none-any.whl", id="erasebuildnum"),
    ],
)
def test_pack(
    tmp_path_factory: TempPathFactory,
    tmp_path: Path,
    build_tag_arg: str | None,
    existing_build_tag: str | None,
    filename: str,
) -> None:
    unpack_dir = tmp_path_factory.mktemp("wheeldir")
    with ZipFile(TESTWHEEL_PATH) as zf:
        old_record = zf.read("test-1.0.dist-info/RECORD")
        old_record_lines = sorted(
            line.rstrip()
            for line in old_record.split(b"\n")
            if line and not line.startswith(b"test-1.0.dist-info/WHEEL,")
        )
        zf.extractall(unpack_dir)

    if existing_build_tag:
        # Add the build number to WHEEL
        wheel_file_path = unpack_dir.joinpath("test-1.0.dist-info").joinpath("WHEEL")
        wheel_file_content = wheel_file_path.read_bytes()
        assert b"Build" not in wheel_file_content
        wheel_file_content += b"Build: 3\r\n"
        wheel_file_path.write_bytes(wheel_file_content)

    args = ["--dest", tmp_path, unpack_dir]
    if build_tag_arg is not None:
        (args.insert(3, "--build"),)
        args.insert(4, build_tag_arg)

    run_command("pack", *args)
    new_wheel_path = tmp_path.joinpath(filename)
    assert new_wheel_path.is_file()

    with ZipFile(new_wheel_path) as zf:
        new_record = zf.read("test-1.0.dist-info/RECORD")
        new_record_lines = sorted(
            line.rstrip()
            for line in new_record.split(b"\n")
            if line and not line.startswith(b"test-1.0.dist-info/WHEEL,")
        )

        parser = BytesParser(policy=email.policy.compat32)
        new_wheel_file_content = parser.parsebytes(zf.read("test-1.0.dist-info/WHEEL"))

    assert new_record_lines == old_record_lines

    # Line endings and trailing blank line will depend on whether WHEEL
    # was modified.  Circumvent this by comparing parsed key/value pairs.
    expected_wheel_content = Message()
    expected_wheel_content["Wheel-Version"] = "1.0"
    expected_wheel_content["Generator"] = "bdist_wheel (0.30.0)"
    expected_wheel_content["Root-Is-Purelib"] = "false"
    expected_wheel_content["Tag"] = "py2-none-any"
    expected_wheel_content["Tag"] = "py3-none-any"
    expected_build_num = (
        build_tag_arg if build_tag_arg is not None else existing_build_tag
    )
    if expected_build_num:
        expected_wheel_content["Build"] = expected_build_num

    assert sorted(new_wheel_file_content.items()) == sorted(
        expected_wheel_content.items()
    )
