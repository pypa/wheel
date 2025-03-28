from __future__ import annotations

import sys
from io import StringIO
from os import PathLike
from subprocess import CalledProcessError
from unittest.mock import patch

import pytest

from wheel._commands import main


def run_command(
    command: str, *args: str | PathLike, catch_systemexit: bool = True
) -> str:
    returncode = 0
    stdout = StringIO()
    stderr = StringIO()
    args = ("wheel", command) + tuple(str(arg) for arg in args)
    with (
        patch.object(sys, "argv", args),
        patch.object(sys, "stdout", stdout),
        patch.object(sys, "stderr", stderr),
    ):
        try:
            main()
        except SystemExit as exc:
            if not catch_systemexit:
                raise CalledProcessError(
                    exc.code, args, stdout.getvalue(), stderr.getvalue()
                ) from exc

            returncode = exc.code

    if returncode:
        pytest.fail(
            f"'wheel {command}' exited with return code {returncode}\n"
            f"arguments: {args}\n"
            f"error output:\n{stderr.getvalue()}"
        )

    return stdout.getvalue()
