from __future__ import annotations

import os.path
import re
import time
from datetime import datetime
from os import PathLike
from pathlib import Path, PurePath
from types import TracebackType
from typing import TYPE_CHECKING
from warnings import warn
from zipfile import ZipInfo

from . import WheelWriter
from ._wheelfile import DEFAULT_TIMESTAMP, WheelError, WheelReader

if TYPE_CHECKING:
    from typing import Literal

warn(
    DeprecationWarning(
        f"The {__name__} module has been deprecated in favor of a supported public "
        "API, and will be removed in a future release."
    )
)

WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>[^\s-]+?)-(?P<ver>[^\s-]+?))(-(?P<build>\d[^\s-]*))?
     -(?P<pyver>[^\s-]+?)-(?P<abi>[^\s-]+?)-(?P<plat>\S+)\.whl$""",
    re.VERBOSE,
)
MINIMUM_TIMESTAMP = 315532800  # 1980-01-01 00:00:00 UTC


def get_zipinfo_datetime(timestamp=None):
    # Some applications need reproducible .whl files, but they can't do this without
    # forcing the timestamp of the individual ZipInfo objects. See issue #143.
    timestamp = int(os.environ.get("SOURCE_DATE_EPOCH", timestamp or time.time()))
    timestamp = max(timestamp, MINIMUM_TIMESTAMP)
    return time.gmtime(timestamp)[0:6]


class WheelFile:
    """Compatibility shim for WheelReader and WheelWriter."""

    _reader: WheelReader
    _writer: WheelWriter

    def __init__(self, path: str | PathLike[str], mode: Literal["r", "w"] = "r"):
        if mode == "r":
            self._reader = WheelReader(path)
        elif mode == "w":
            self._writer = WheelWriter(path)
        else:
            raise ValueError(f"Invalid mode: {mode}")

        self.filename = str(path)
        parsed_filename = WHEEL_INFO_RE.match(os.path.basename(self.filename))
        if parsed_filename is None:
            raise WheelError("Cannot parse wheel file name")

        self.parsed_filename = parsed_filename

    @property
    def dist_info_path(self) -> str:
        if hasattr(self, "_reader"):
            return self._reader._dist_info_dir
        else:
            return self._writer._dist_info_dir

    def __enter__(self) -> WheelFile:
        if hasattr(self, "_reader"):
            self._reader.__enter__()
        else:
            self._writer.__enter__()

        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        if hasattr(self, "_reader"):
            self._reader.__exit__(exc_type, exc_val, exc_tb)
        else:
            self._writer.__exit__(exc_type, exc_val, exc_tb)

    def read(self, name: str) -> bytes:
        return self._reader.read_file(name)

    def extractall(self, base_path: str | PathLike[str] | None = None) -> None:
        self._reader.extractall(base_path or os.getcwd())

    def write_files(self, base_dir: PathLike[str] | str) -> None:
        self._writer.write_files_from_directory(base_dir)

    def write(
        self,
        filename: str | PathLike[str],
        arcname: str | None = None,
        compress_type: int | None = None,
    ):
        fname = PurePath(arcname or filename)
        self._writer.write_file(fname, Path(filename))

    def writestr(
        self,
        zinfo_or_arcname: str | ZipInfo,
        data: bytes | str,
        compress_type: int | None = None,
    ):
        if isinstance(data, str):
            data = data.encode("utf-8")

        if isinstance(zinfo_or_arcname, ZipInfo):
            arcname = zinfo_or_arcname.filename
            timestamp = datetime(*zinfo_or_arcname.date_time[:6])
        elif isinstance(zinfo_or_arcname, str):
            arcname = zinfo_or_arcname
            timestamp = DEFAULT_TIMESTAMP
        else:
            raise TypeError(
                f"Invalid type for zinfo_or_arcname: {type(zinfo_or_arcname)}"
            )

        self._writer.write_file(arcname, data, timestamp=timestamp)
