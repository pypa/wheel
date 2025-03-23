from __future__ import annotations

import subprocess
from os import PathLike

import pytest


def run_command(command: str, *args: str | PathLike, check: bool = False) -> str:
    arguments = ["wheel", command, *args]
    process = subprocess.run(arguments, capture_output=True, text=True, check=check)
    if process.returncode:
        pytest.fail(
            f"'wheel {command}' exited with return code {process.returncode}\n"
            f"arguments: {args}\n"
            f"error output:\n{process.stderr}"
        )

    return process.stdout
