from __future__ import annotations

import csv
import hashlib
import os.path
import re
import stat
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import OrderedDict
from collections.abc import Iterable, Iterator
from contextlib import ExitStack
from datetime import datetime, timezone
from email.generator import Generator
from email.message import Message
from io import StringIO, UnsupportedOperation
from os import PathLike
from pathlib import Path, PurePath
from types import TracebackType
from typing import IO, NamedTuple
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

from . import __version__ as wheel_version
from .vendored.packaging.tags import Tag
from .vendored.packaging.utils import (
    InvalidWheelFilename,
    NormalizedName,
    parse_wheel_filename,
)
from .vendored.packaging.version import Version

_DIST_NAME_RE = re.compile(r"[^A-Za-z0-9.]+")
_EXCLUDE_FILENAMES = ("RECORD", "RECORD.jws", "RECORD.p7s")
DEFAULT_TIMESTAMP = datetime(1980, 1, 1, tzinfo=timezone.utc)


class WheelMetadata(NamedTuple):
    name: NormalizedName
    version: Version
    build_tag: tuple[int, str] | tuple[()]
    tags: frozenset[Tag]

    @classmethod
    def from_filename(cls, fname: str) -> WheelMetadata:
        try:
            name, version, build, tags = parse_wheel_filename(fname)
        except InvalidWheelFilename as exc:
            raise WheelError(f"Bad wheel filename {fname!r}") from exc

        return cls(name, version, build, tags)


class WheelRecordEntry(NamedTuple):
    hash_algorithm: str
    hash_value: bytes
    filesize: int


class WheelContentElement(NamedTuple):
    path: PurePath
    hash_value: bytes
    size: int
    stream: IO[bytes]


def _encode_hash_value(hash_value: bytes) -> str:
    return urlsafe_b64encode(hash_value).rstrip(b"=").decode("ascii")


def _decode_hash_value(encoded_hash: str) -> bytes:
    pad = b"=" * (4 - (len(encoded_hash) & 3))
    return urlsafe_b64decode(encoded_hash.encode("ascii") + pad)


def make_filename(
    name: str,
    version: str,
    build_tag: str | int | None = None,
    impl_tag: str = "py3",
    abi_tag: str = "none",
    plat_tag: str = "any",
) -> str:
    name = _DIST_NAME_RE.sub("_", name)
    version = _DIST_NAME_RE.sub("_", version)
    filename = f"{name}-{version}"
    if build_tag:
        filename = f"{filename}-{build_tag}"

    return f"{filename}-{impl_tag}-{abi_tag}-{plat_tag}.whl"


class WheelError(Exception):
    pass


class WheelArchiveFile:
    def __init__(
        self, fp: IO[bytes], arcname: str, record_entry: WheelRecordEntry | None
    ):
        self._fp = fp
        self._arcname = arcname
        self._record_entry = record_entry
        if record_entry:
            self._hash = hashlib.new(record_entry.hash_algorithm)
            self._num_bytes_read = 0

    def read(self, amount: int = -1) -> bytes:
        data = self._fp.read(amount)
        if amount and self._record_entry is not None:
            if data:
                self._hash.update(data)
                self._num_bytes_read += len(data)
            elif self._record_entry:
                # The file has been read in full – check that hash and file size match
                # with the entry in RECORD
                if self._hash.digest() != self._record_entry.hash_value:
                    raise WheelError(f"Hash mismatch for file {self._arcname!r}")
                elif self._num_bytes_read != self._record_entry.filesize:
                    raise WheelError(
                        f"{self._arcname}: file size mismatch: "
                        f"{self._record_entry.filesize} bytes in RECORD, "
                        f"{self._num_bytes_read} bytes in archive"
                    )

        return data

    def __enter__(self) -> WheelArchiveFile:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._fp.close()

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self._fp!r}, {self._arcname!r})"


class WheelReader:
    name: NormalizedName
    version: Version
    _zip: ZipFile
    _record_entries: OrderedDict[str, WheelRecordEntry]

    def __init__(self, path_or_fd: str | PathLike[str] | IO[bytes]):
        self.path_or_fd = path_or_fd

        if isinstance(path_or_fd, (str, PathLike)):
            fname = Path(path_or_fd).name
            try:
                self.name, self.version = parse_wheel_filename(fname)[:2]
            except InvalidWheelFilename as exc:
                raise WheelError(str(exc)) from None

    def __enter__(self) -> WheelReader:
        self._zip = ZipFile(self.path_or_fd, "r")
        try:
            if not hasattr(self, "name"):
                for zinfo in reversed(self._zip.infolist()):
                    if zinfo.is_dir() and zinfo.filename.endswith(".dist-info"):
                        match = _DIST_NAME_RE.match(zinfo.filename)
                        if match:
                            self.name = NormalizedName(match[1])
                            self.version = Version(match[2])
                            break
                else:
                    raise WheelError(
                        "Cannot find a .dist-info directory. Is this really a wheel "
                        "file?"
                    )
        except BaseException:
            self._zip.close()
            raise

        self._dist_info_dir = f"{self.name}-{self.version}.dist-info"
        self._data_dir = f"{self.name}-{self.version}.data"
        self._record_entries = self._read_record()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        self._zip.close()
        self._record_entries.clear()

    def _read_record(self) -> OrderedDict[str, WheelRecordEntry]:
        entries = OrderedDict()
        contents = self.read_dist_info("RECORD")
        reader = csv.reader(
            contents.strip().split("\n"),
            delimiter=",",
            quotechar='"',
            lineterminator="\n",
        )
        for row in reader:
            if not row:
                break

            path, hash_digest, filesize = row
            if hash_digest:
                algorithm, hash_digest = hash_digest.split("=")
                try:
                    hashlib.new(algorithm)
                except ValueError:
                    raise WheelError(
                        f"Unsupported hash algorithm: {algorithm}"
                    ) from None

                if algorithm.lower() in {"md5", "sha1"}:
                    raise WheelError(
                        f"Weak hash algorithm ({algorithm}) is not permitted by PEP 427"
                    )

                entries[path] = WheelRecordEntry(
                    algorithm, _decode_hash_value(hash_digest), int(filesize)
                )

        return entries

    @property
    def dist_info_dir(self) -> str:
        return self._dist_info_dir

    @property
    def data_dir(self) -> str:
        return self._data_dir

    @property
    def dist_info_filenames(self) -> list[PurePath]:
        return [
            PurePath(fname)
            for fname in self._zip.namelist()
            if fname.startswith(self._dist_info_dir)
        ]

    @property
    def filenames(self) -> list[PurePath]:
        return [PurePath(fname) for fname in self._zip.namelist()]

    def read_dist_info(self, filename: str) -> str:
        filename = self.dist_info_dir + "/" + filename
        try:
            contents = self._zip.read(filename)
        except KeyError:
            raise WheelError(f"File {filename!r} not found") from None

        return contents.decode("utf-8")

    def get_contents(self) -> Iterator[WheelContentElement]:
        for fname, entry in self._record_entries.items():
            with self._zip.open(fname, "r") as stream:
                yield WheelContentElement(
                    PurePath(fname), entry.hash_value, entry.filesize, stream
                )

    def test(self) -> None:
        """Verify the integrity of the contained files."""
        for zinfo in self._zip.infolist():
            # Ignore signature files
            basename = os.path.basename(zinfo.filename)
            if basename in _EXCLUDE_FILENAMES:
                continue

            try:
                record = self._record_entries[zinfo.filename]
            except KeyError:
                raise WheelError(f"No hash found for file {zinfo.filename!r}") from None

            hash_ = hashlib.new(record.hash_algorithm)
            with self._zip.open(zinfo) as fp:
                hash_.update(fp.read(65536))

            if hash_.digest() != record.hash_value:
                raise WheelError(f"Hash mismatch for file {zinfo.filename!r}")

    def extractall(self, base_path: str | PathLike[str]) -> None:
        basedir = Path(base_path)
        if not basedir.exists():
            raise WheelError(f"{basedir} does not exist")
        elif not basedir.is_dir():
            raise WheelError(f"{basedir} is not a directory")

        for fname in self._zip.namelist():
            target_path = basedir.joinpath(fname)
            target_path.parent.mkdir(0o755, True, True)
            with self._open_file(fname) as infile, target_path.open("wb") as outfile:
                while True:
                    data = infile.read(65536)
                    if not data:
                        break

                    outfile.write(data)

    def _open_file(self, archive_name: str) -> WheelArchiveFile:
        basename = os.path.basename(archive_name)
        if basename in _EXCLUDE_FILENAMES:
            record_entry = None
        else:
            record_entry = self._record_entries[archive_name]

        return WheelArchiveFile(
            self._zip.open(archive_name), archive_name, record_entry
        )

    def _read_file(self, archive_name: str) -> bytes:
        with self._open_file(archive_name) as fp:
            return fp.read()

    def read_data_file(self, filename: str) -> bytes:
        archive_path = self._data_dir + "/" + filename.strip("/")
        return self._read_file(archive_path)

    def read_distinfo_file(self, filename: str) -> bytes:
        archive_path = self._dist_info_dir + "/" + filename.strip("/")
        return self._read_file(archive_path)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.path_or_fd})"


class WheelWriter:
    def __init__(
        self,
        path_or_fd: str | PathLike[str] | IO[bytes],
        metadata: WheelMetadata | None = None,
        *,
        generator: str | None = None,
        root_is_purelib: bool = True,
        compress: bool = True,
        hash_algorithm: str = "sha256",
    ):
        self.path_or_fd = path_or_fd
        self.generator = generator or f"Wheel ({wheel_version})"
        self.root_is_purelib = root_is_purelib
        self.hash_algorithm = hash_algorithm
        self._compress_type = ZIP_DEFLATED if compress else ZIP_STORED

        if metadata:
            self.metadata = metadata
        elif isinstance(path_or_fd, (str, PathLike)):
            filename = Path(path_or_fd).name
            self.metadata = WheelMetadata.from_filename(filename)
        else:
            raise WheelError("path_or_fd is not a path, and metadata was not provided")

        if hash_algorithm not in hashlib.algorithms_available:
            raise ValueError(f"Hash algorithm {hash_algorithm!r} is not available")
        elif hash_algorithm in ("md5", "sha1"):
            raise ValueError(
                f"Weak hash algorithm ({hash_algorithm}) is not permitted by PEP 427"
            )

        self._dist_info_dir = f"{self.metadata.name}-{self.metadata.version}.dist-info"
        self._data_dir = f"{self.metadata.name}-{self.metadata.version}.data"
        self._record_path = f"{self._dist_info_dir}/RECORD"
        self._record_entries: dict[str, WheelRecordEntry] = OrderedDict()

    def __enter__(self) -> WheelWriter:
        self._zip = ZipFile(self.path_or_fd, "w", compression=self._compress_type)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException],
        exc_val: BaseException,
        exc_tb: TracebackType,
    ) -> None:
        try:
            if not exc_type:
                if f"{self._dist_info_dir}/WHEEL" not in self._record_entries:
                    self._write_wheelfile()

                self._write_record()
        finally:
            self._zip.close()

    def _write_record(self) -> None:
        data = StringIO()
        writer = csv.writer(data, delimiter=",", quotechar='"', lineterminator="\n")
        writer.writerows(
            [
                (
                    fname,
                    entry.hash_algorithm + "=" + _encode_hash_value(entry.hash_value),
                    entry.filesize,
                )
                for fname, entry in self._record_entries.items()
            ]
        )
        writer.writerow((self._record_path, "", ""))
        self.write_distinfo_file("RECORD", data.getvalue())

    def _write_wheelfile(self) -> None:
        msg = Message()
        msg["Wheel-Version"] = "1.0"  # of the spec
        msg["Generator"] = self.generator
        msg["Root-Is-Purelib"] = str(self.root_is_purelib).lower()
        if self.metadata.build_tag:
            msg["Build"] = str(self.metadata.build_tag[0]) + self.metadata.build_tag[1]

        for tag in sorted(
            self.metadata.tags, key=lambda t: (t.interpreter, t.abi, t.platform)
        ):
            msg["Tag"] = f"{tag.interpreter}-{tag.abi}-{tag.platform}"

        buffer = StringIO()
        Generator(buffer, maxheaderlen=0).flatten(msg)
        self.write_distinfo_file("WHEEL", buffer.getvalue())

    def write_metadata(self, items: Iterable[tuple[str, str]]) -> None:
        msg = Message()
        for key, value in items:
            key = key.title()
            if key == "Description":
                msg.set_payload(value, "utf-8")
            else:
                msg.add_header(key, value)

        if "Metadata-Version" not in msg:
            msg["Metadata-Version"] = "2.1"
        if "Name" not in msg:
            msg["Name"] = self.metadata.name
        if "Version" not in msg:
            msg["Version"] = str(self.metadata.version)

        buffer = StringIO()
        Generator(buffer, maxheaderlen=0).flatten(msg)
        self.write_distinfo_file("METADATA", buffer.getvalue())

    def write_file(
        self,
        name: str | PurePath,
        contents: bytes | str | PathLike[str] | IO[bytes],
        timestamp: datetime = DEFAULT_TIMESTAMP,
    ) -> None:
        arcname = PurePath(name).as_posix()
        gmtime = time.gmtime(timestamp.timestamp())
        zinfo = ZipInfo(arcname, gmtime[:6])
        zinfo.compress_type = self._compress_type
        zinfo.external_attr = 0o664 << 16
        with ExitStack() as exit_stack:
            fp = exit_stack.enter_context(self._zip.open(zinfo, "w"))
            if isinstance(contents, str):
                contents = contents.encode("utf-8")
            elif isinstance(contents, PathLike):
                contents = exit_stack.enter_context(Path(contents).open("rb"))

            if isinstance(contents, bytes):
                file_size = len(contents)
                fp.write(contents)
                hash_ = hashlib.new(self.hash_algorithm, contents)
            else:
                try:
                    st = os.stat(contents.fileno())
                except (AttributeError, UnsupportedOperation):
                    pass
                else:
                    zinfo.external_attr = (
                        stat.S_IMODE(st.st_mode) | stat.S_IFMT(st.st_mode)
                    ) << 16

                hash_ = hashlib.new(self.hash_algorithm)
                while True:
                    buffer = contents.read(65536)
                    if not buffer:
                        file_size = contents.tell()
                        break

                    hash_.update(buffer)
                    fp.write(buffer)

        self._record_entries[arcname] = WheelRecordEntry(
            self.hash_algorithm, hash_.digest(), file_size
        )

    def write_files_from_directory(self, directory: str | PathLike[str]) -> None:
        basedir = Path(directory)
        if not basedir.exists():
            raise WheelError(f"{basedir} does not exist")
        elif not basedir.is_dir():
            raise WheelError(f"{basedir} is not a directory")

        for root, _dirs, files in os.walk(basedir):
            for fname in files:
                path = Path(root) / fname
                relative = path.relative_to(basedir)
                if relative.as_posix() != self._record_path:
                    self.write_file(relative, path)

    def write_data_file(
        self,
        filename: str,
        contents: bytes | str | PathLike[str] | IO[bytes],
        timestamp: datetime = DEFAULT_TIMESTAMP,
    ) -> None:
        archive_path = self._data_dir + "/" + filename.strip("/")
        self.write_file(archive_path, contents, timestamp)

    def write_distinfo_file(
        self,
        filename: str,
        contents: bytes | str | IO[bytes],
        timestamp: datetime = DEFAULT_TIMESTAMP,
    ) -> None:
        archive_path = self._dist_info_dir + "/" + filename.strip()
        self.write_file(archive_path, contents, timestamp)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.path_or_fd!r})"
