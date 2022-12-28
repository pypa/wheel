from __future__ import annotations

import os
import re
import zipfile
from collections.abc import Generator, Iterable
from email.message import Message
from email.parser import HeaderParser
from os import PathLike
from pathlib import Path, PurePath
from typing import IO, Any

from .. import WheelWriter, make_filename
from . import WheelError

egg_info_re = re.compile(
    r"""
    (?P<name>.+?)-(?P<ver>.+?)
    (-(?P<pyver>py\d\.\d+)
     (-(?P<arch>.+?))?
    )?.egg$""",
    re.VERBOSE,
)


def egg2wheel(egg_path: Path, dest_dir: Path) -> None:
    def egg_file_source() -> Generator[tuple[PurePath, IO[bytes]], Any, None]:
        with zipfile.ZipFile(egg_path) as zf:
            for zinfo in zf.infolist():
                with zf.open(zinfo) as fp:
                    yield PurePath(zinfo.filename), fp

    def egg_dir_source() -> Generator[tuple[PurePath, IO[bytes]], Any, None]:
        for root, _dirs, files in os.walk(egg_path, followlinks=False):
            root_path = Path(root)
            for fname in files:
                file_path = root_path / fname
                with file_path.open("rb") as fp:
                    yield file_path, fp

    match = egg_info_re.match(egg_path.name)
    if not match:
        raise WheelError(f"Invalid egg file name: {egg_path.name}")

    # Assume pure Python if there is no specified architecture
    # Assume all binary eggs are for CPython
    egg_info = match.groupdict()
    pyver = egg_info["pyver"].replace(".", "")
    arch = (egg_info["arch"] or "any").replace(".", "_").replace("-", "_")
    abi = "cp" + pyver[2:] if arch != "any" else "none"
    root_is_purelib = arch is None

    if egg_path.is_dir():
        # buildout-style installed eggs directory
        source = egg_dir_source()
    else:
        source = egg_file_source()

    wheel_name = make_filename(
        egg_info["name"], egg_info["ver"], impl_tag=pyver, abi_tag=abi, plat_tag=arch
    )
    metadata = Message()
    with WheelWriter(
        dest_dir / wheel_name, generator="egg2wheel", root_is_purelib=root_is_purelib
    ) as wf:
        for path, fp in source:
            if path.parts[0] == "EGG-INFO":
                if path.parts[1] == "requires.txt":
                    requires = fp.read().decode("utf-8")
                    extra = specifier = ""
                    for line in requires.splitlines():
                        line = line.strip()
                        if line.startswith("[") and line.endswith("]"):
                            extra, _, specifier = line[1:-1].strip().partition(":")
                            metadata["Provides-Extra"] = extra
                        elif line:
                            specifiers: list[str] = []
                            if extra:
                                specifiers += f"extra == {extra!r}"

                            if specifier:
                                specifiers += specifier

                            if specifiers:
                                line = line + " ; " + " and ".join(specifiers)

                            metadata["Requires-Dist"] = line
                elif path.parts[1] in ("entry_points.txt", "top_level.txt"):
                    wf.write_distinfo_file(path.parts[1], fp)
                elif path.parts[1] == "PKG-INFO":
                    pkg_info = HeaderParser().parsestr(fp.read().decode("utf-8"))
                    pkg_info.replace_header("Metadata-Version", "2.1")
                    del pkg_info["Provides-Extra"]
                    del pkg_info["Requires-Dist"]
                    for header, value in pkg_info.items():
                        metadata[header] = value
            else:
                wf.write_file(path, fp)

        if metadata:
            wf.write_metadata(metadata.items())


def convert(
    files: Iterable[str | PathLike[str]], dest_dir: str | PathLike[str], verbose: bool
) -> None:
    dest_path = Path(dest_dir)
    paths: list[Path] = []
    for fname in files:
        path = Path(fname)
        if path.is_file():
            paths.append(path)
        elif path.is_dir():
            paths.extend(path.iterdir())

    for path in paths:
        if path.suffix != ".egg":
            continue

        if verbose:
            print(f"{path}... ", flush=True)

        egg2wheel(path, dest_path)

        if verbose:
            print("OK")
