import csv
import hashlib
import os.path
import re
import sys
import time
from base64 import urlsafe_b64decode, urlsafe_b64encode
from collections import OrderedDict
from datetime import datetime
from email.generator import Generator
from email.message import Message
from email.parser import Parser
from io import StringIO
from pathlib import Path
from typing import Optional, Union, Dict, Iterable, NamedTuple, IO, Tuple, List
from zipfile import ZIP_DEFLATED, ZipInfo, ZipFile

from . import __version__ as wheel_version

if sys.version_info >= (3, 6):
    from os import PathLike
else:
    PathLike = Path

_DIST_NAME_RE = re.compile(r'[^A-Za-z0-9.]+')
_WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)-(?P<ver>.+?))(?:-(?P<build>\d[^-]*))?
     -(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)\.whl$""",
    re.VERBOSE)

WheelMetadata = NamedTuple('WheelMetadata', [
    ('name', str),
    ('version', str),
    ('build_tag', Optional[str]),
    ('implementation', str),
    ('abi', str),
    ('platform', str)
])

WheelRecordEntry = NamedTuple('_WheelRecordEntry', [
    ('hash_algorithm', str),
    ('hash_value', bytes),
    ('filesize', int)
])


def _encode_hash_value(hash_value: bytes) -> str:
    return urlsafe_b64encode(hash_value).rstrip(b'=').decode('ascii')


def _decode_hash_value(encoded_hash: str) -> bytes:
    pad = b'=' * (4 - (len(encoded_hash) & 3))
    return urlsafe_b64decode(encoded_hash.encode('ascii') + pad)


def parse_filename(filename: str) -> WheelMetadata:
    parsed_filename = _WHEEL_INFO_RE.match(filename)
    if parsed_filename is None:
        raise WheelError('Bad wheel filename {!r}'.format(filename))

    return WheelMetadata(*parsed_filename.groups()[1:])


def make_filename(name: str, version: str, build_tag: Union[str, int, None] = None,
                  impl_tag: str = 'py3', abi_tag: str = 'none', plat_tag: str = 'any') -> str:
    name = _DIST_NAME_RE.sub('_', name)
    version = _DIST_NAME_RE.sub('_', version)
    filename = '{}-{}'.format(name, version)
    if build_tag is not None:
        filename = '{}-{}'.format(filename, build_tag)

    return '{}-{}-{}-{}.whl'.format(filename, impl_tag, abi_tag, plat_tag)


class WheelError(Exception):
    pass


class WheelFile:
    __slots__ = ('generator', 'root_is_purelib', '_mode', '_metadata', '_compression', '_zip',
                 '_data_path', '_dist_info_path', '_record_path', '_record_entries',
                 '_exclude_archive_names')

    # dist-info file names ignored for hash checking/recording
    _exclude_filenames = ('RECORD', 'RECORD.jws', 'RECORD.p7s')
    _default_hash_algorithm = 'sha256'

    def __init__(self, path_or_fd: Union[str, PathLike, IO[bytes]], mode: str = 'r', *,
                 metadata: Optional[WheelMetadata] = None, compression: int = ZIP_DEFLATED,
                 generator: Optional[str] = None, root_is_purelib: bool = True):
        if mode not in ('r', 'w'):
            raise ValueError("mode must be either 'r' or 'w'")

        if isinstance(path_or_fd, (str, PathLike)):
            path_or_fd = Path(path_or_fd).open(mode + 'b')

        if metadata is None:
            filename = getattr(path_or_fd, 'name', None)
            if filename:
                metadata = parse_filename(os.path.basename(filename))
            else:
                raise WheelError('No file name or metadata provided')

        self.generator = generator or 'Wheel {}'.format(wheel_version)
        self.root_is_purelib = root_is_purelib
        self._mode = mode
        self._metadata = metadata
        self._compression = compression
        self._data_path = '{meta.name}-{meta.version}.data'.format(meta=self._metadata)
        self._dist_info_path = '{meta.name}-{meta.version}.dist-info'.format(meta=self._metadata)
        self._record_path = self._dist_info_path + '/RECORD'
        self._exclude_archive_names = frozenset(self._dist_info_path + '/' + fname
                                                for fname in self._exclude_filenames)
        self._zip = ZipFile(path_or_fd, mode)
        self._record_entries = OrderedDict()  # type: Dict[str, WheelRecordEntry]

        if mode == 'r':
            self._read_record()

    @property
    def path(self) -> Optional[Path]:
        return Path(self._zip.filename) if self._zip.filename else None

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def metadata(self) -> WheelMetadata:
        return self._metadata

    @property
    def record_entries(self) -> Dict[str, WheelRecordEntry]:
        return self._record_entries.copy()

    @property
    def filenames(self) -> List[str]:
        return self._zip.namelist()

    def close(self) -> None:
        try:
            if self.mode == 'w':
                filenames = set(self._zip.namelist())

                metadata_path = self._dist_info_path + '/METADATA'
                if metadata_path not in filenames:
                    self.write_metadata([])

                wheel_path = self._dist_info_path + '/WHEEL'
                if wheel_path not in filenames:
                    self._write_wheelfile()

                self._write_record()
        except BaseException:
            self._zip.close()
            if self.mode == 'w' and self._zip.filename:
                os.unlink(self._zip.filename)

            raise
        finally:
            try:
                self._zip.close()
            finally:
                self._record_entries.clear()

    def __enter__(self) -> 'WheelFile':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def write_file(self, archive_name: str, contents: Union[bytes, str],
                   timestamp: Union[datetime, int] = None) -> None:
        if isinstance(contents, str):
            contents = contents.encode('utf-8')
        elif not isinstance(contents, bytes):
            raise TypeError('contents must be str or bytes')

        if timestamp is None:
            timestamp = time.time()
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.timestamp()
        elif not isinstance(timestamp, int):
            raise TypeError('timestamp must be int or datetime (or None to use current time')

        if archive_name not in self._exclude_archive_names:
            hash_digest = hashlib.new(self._default_hash_algorithm, contents).digest()
            self._record_entries[archive_name] = WheelRecordEntry(
                self._default_hash_algorithm, hash_digest, len(contents))

        zinfo = ZipInfo(archive_name, date_time=time.gmtime(timestamp)[0:6])
        zinfo.compress_type = self._compression
        zinfo.external_attr = 0o664 << 16
        self._zip.writestr(zinfo, contents)

    def write_data_file(self, filename: str, contents: Union[bytes, str],
                        timestamp: Union[datetime, int] = None) -> None:
        archive_path = self._data_path + '/' + filename.strip('/')
        self.write_file(archive_path, contents, timestamp)

    def write_distinfo_file(self, filename: str, contents: Union[bytes, str],
                            timestamp: Union[datetime, int] = None) -> None:
        archive_path = self._dist_info_path + '/' + filename.strip()
        self.write_file(archive_path, contents, timestamp)

    def read_file(self, archive_name: str) -> bytes:
        try:
            contents = self._zip.read(archive_name)
        except KeyError:
            raise WheelError('File {} not found'.format(archive_name)) from None

        if archive_name in self._record_entries:
            entry = self._record_entries[archive_name]
            if len(contents) != entry.filesize:
                raise WheelError('{}: file size mismatch: {} bytes in RECORD, {} bytes in archive'
                                 .format(archive_name, entry.filesize, len(contents)))

            computed_hash = hashlib.new(entry.hash_algorithm, contents).digest()
            if computed_hash != entry.hash_value:
                raise WheelError(
                    '{}: hash mismatch: {} in RECORD, {} computed from current file contents'
                    .format(archive_name, _encode_hash_value(entry.hash_value),
                            _encode_hash_value(computed_hash)))

        return contents

    def read_data_file(self, filename: str) -> bytes:
        archive_path = self._data_path + '/' + filename.strip('/')
        return self.read_file(archive_path)

    def read_distinfo_file(self, filename: str) -> bytes:
        archive_path = self._dist_info_path + '/' + filename.strip('/')
        return self.read_file(archive_path)

    def unpack(self, dest_dir: Union[str, PathLike],
               archive_names: Union[str, Iterable[str], None] = None) -> None:
        base_path = Path(dest_dir)
        if not base_path.is_dir():
            raise WheelError('{} is not a directory'.format(base_path))

        if archive_names is None:
            filenames = self._zip.infolist()
        elif isinstance(archive_names, str):
            filenames = [self._zip.getinfo(archive_names)]
        else:
            filenames = [self._zip.getinfo(fname) for fname in archive_names]

        for zinfo in filenames:
            entry = None  # type: Optional[WheelRecordEntry]
            if zinfo.filename in self._record_entries:
                entry = self._record_entries[zinfo.filename]

            path = base_path.joinpath(zinfo.filename)
            with self._zip.open(zinfo) as infile, path.open('wb') as outfile:
                hash_ = hashlib.new(entry.hash_algorithm) if entry else None
                while True:
                    data = infile.read(1024 * 1024)
                    if data:
                        if hash_:
                            hash_.update(data)

                        outfile.write(data)
                    else:
                        break

            if hash_ is not None and entry is not None and hash_.digest() != entry.hash_value:
                raise WheelError(
                    '{}: hash mismatch: {} in RECORD, {} computed from current file contents'
                    .format(zinfo.filename, _encode_hash_value(entry.hash_value),
                            _encode_hash_value(hash_.digest()))
                )

    def _read_record(self) -> None:
        self._record_entries.clear()
        contents = self.read_distinfo_file('RECORD').decode('utf-8')
        for line in contents.strip().split('\n'):
            path, hash_digest, filesize = line.rsplit(',', 2)
            if hash_digest:
                algorithm, hash_digest = hash_digest.split('=')
                try:
                    hashlib.new(algorithm)
                except ValueError:
                    raise WheelError('Unsupported hash algorithm: {}'.format(algorithm))

                if algorithm.lower() in {'md5', 'sha1'}:
                    raise WheelError(
                        'Weak hash algorithm ({}) is not permitted by PEP 427'
                        .format(algorithm))

                self._record_entries[path] = WheelRecordEntry(
                    algorithm, _decode_hash_value(hash_digest), int(filesize))

    def _write_record(self) -> None:
        data = StringIO()
        writer = csv.writer(data, delimiter=',', quotechar='"', lineterminator='\n')
        writer.writerows([
            (fname,
             entry.hash_algorithm + "=" + _encode_hash_value(entry.hash_value),
             entry.filesize)
            for fname, entry in self._record_entries.items()
        ])
        writer.writerow((self._record_path, "", ""))
        self.write_distinfo_file('RECORD', data.getvalue())

    def _write_wheelfile(self) -> None:
        msg = Message()
        msg['Wheel-Version'] = '1.0'  # of the spec
        msg['Generator'] = self.generator
        msg['Root-Is-Purelib'] = str(self.root_is_purelib).lower()
        if self.metadata.build_tag is not None:
            msg['Build'] = self.metadata.build_tag

        for impl in self.metadata.implementation.split('.'):
            for abi in self.metadata.abi.split('.'):
                for plat in self.metadata.platform.split('.'):
                    msg['Tag'] = '-'.join((impl, abi, plat))

        buffer = StringIO()
        Generator(buffer, maxheaderlen=0).flatten(msg)
        self.write_distinfo_file('WHEEL', buffer.getvalue())

    def read_metadata(self) -> List[Tuple[str, str]]:
        contents = self.read_distinfo_file('METADATA').decode('utf-8')
        msg = Parser().parsestr(contents)
        items = [(key, str(value)) for key, value in msg.items()]
        payload = msg.get_payload(0, True)
        if payload:
            items.append(('Description', payload))

        return items

    def write_metadata(self, items: Iterable[Tuple[str, str]]) -> None:
        msg = Message()
        for key, value in items:
            key = key.title()
            if key == 'Description':
                msg.set_payload(value, 'utf-8')
            else:
                msg.add_header(key, value)

        if 'Metadata-Version' not in msg:
            msg['Metadata-Version'] = '2.1'
        if 'Name' not in msg:
            msg['Name'] = self._metadata.name
        if 'Version' not in msg:
            msg['Version'] = self._metadata.version

        buffer = StringIO()
        Generator(buffer, maxheaderlen=0).flatten(msg)
        self.write_distinfo_file('METADATA', buffer.getvalue())

    def __repr__(self):
        return '{}({!r}, {!r})'.format(self.__class__.__name__, self.path, self.mode)
