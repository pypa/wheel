"""Install a wheel
"""
# XXX see patched pip to install

import sys
import os.path
import re
import zipfile
import hmac
import hashlib
import csv
from email.parser import Parser

from wheel.decorator import reify
from wheel.util import urlsafe_b64encode, utf8, to_json, from_json,\
    urlsafe_b64decode, native, binary
from wheel import signatures

# The next major version after this version of the 'wheel' tool:
VERSION_TOO_HIGH = (1, 0)

# Non-greedy matching of an optional build number may be too clever (more
# invalid wheel filenames will match). Separate regex for .dist-info?
WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)(-(?P<ver>\d.+?))?)
    ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
    \.whl|\.dist-info)$""",
    re.VERBOSE).match


class BadWheelFile(ValueError):
    pass


class WheelFile(object):
    """Parse wheel-specific attributes from a wheel (.whl) file"""
    WHEEL_INFO = "WHEEL"

    def __init__(self, filename, append=False):
        """
        :param append: Open archive in append mode.
        """
        self.filename = filename
        self.append = append
        basename = os.path.basename(filename)
        self.parsed_filename = WHEEL_INFO_RE(basename)
        if not basename.endswith('.whl') or self.parsed_filename is None:
            raise BadWheelFile("Bad filename '%s'" % filename)

    def __repr__(self):
        return self.filename

    @reify
    def zipfile(self):
        mode = "r"
        if self.append:
            mode = "a"
        vzf = VerifyingZipFile(self.filename, mode)
        if not self.append:
            self.verify(vzf)
        return vzf

    def get_metadata(self):
        pass

    @property
    def distinfo_name(self):
        return "%s.dist-info" % self.parsed_filename.group('namever')

    @property
    def datadir_name(self):
        return "%s.data" % self.parsed_filename.group('namever')

    @property
    def wheelinfo_name(self):
        return "%s/%s" % (self.distinfo_name, self.WHEEL_INFO)

    @property
    def compatibility_tags(self):
        """A wheel file is compatible with the Cartesian product of the
        period-delimited tags in its filename.
        To choose a wheel file among several candidates having the same
        distribution version 'ver', an installer ranks each triple of
        (pyver, abi, plat) that its Python installation can run, sorting
        the wheels by the best-ranked tag it supports and then by their
        arity which is just len(list(compatibility_tags)).
        """
        tags = self.parsed_filename.groupdict()
        for pyver in tags['pyver'].split('.'):
            for abi in tags['abi'].split('.'):
                for plat in tags['plat'].split('.'):
                    yield (pyver, abi, plat)

    @property
    def arity(self):
        '''The number of compatibility tags the wheel is compatible with.'''
        return len(list(self.compatibility_tags))

    def compatibility_rank(self, supported):
        '''Rank the wheel against the supported ones.

        :param supported: A list of compatibility tags that the current
            Python implemenation can run.
        '''
        preferences = []
        for tag in self.compatibility_tags:
            try:
                preferences.append(supported.index(tag))
            # Tag not present
            except ValueError:
                pass
        return (min(preferences), self.arity)

    @reify
    def parsed_wheel_info(self):
        """Parse wheel metadata"""
        return Parser().parse(self.zipfile.open(self.wheelinfo_name))

    def check_version(self):
        version = self.parsed_wheel_info['Wheel-Version']
        if tuple(map(int, version.split('.'))) >= VERSION_TOO_HIGH:
            raise ValueError("Wheel version is too high")
        
    def verify(self, zipfile=None):
        """Verify the VerifyingZipFile `zipfile` by verifying its signature 
        and setting expected hashes for every hash in RECORD.
        Caller must complete the verification process by completely reading 
        every file in the archive (e.g. with extractall)."""
        sig = None
        if zipfile is None:
            zipfile = self.zipfile
        zipfile.strict = True
        
        record_name = '/'.join((self.distinfo_name, 'RECORD'))
        sig_name = '/'.join((self.distinfo_name, 'RECORD.jws'))
        zipfile.set_expected_hash(record_name, None)
        zipfile.set_expected_hash(sig_name, None)
        record = zipfile.read(record_name)
                
        record_digest = urlsafe_b64encode(hashlib.sha256(record).digest())
        try:
            sig = from_json(zipfile.read(sig_name))
        except KeyError: # no signature
            pass
        if sig:
            headers, payload = signatures.verify(sig)
            if payload['hash'] != "sha256=" + record_digest:
                raise BadWheelFile("Claimed RECORD hash != computed hash.")
        
        reader = csv.reader((native(r) for r in record.splitlines()))
        
        for row in reader:
            filename = row[0]
            hash = row[1]
            if not hash:
                if filename not in (record_name, sig_name):
                    sys.stderr.write("%s has no hash!\n" % filename)
                continue
            algo, data = row[1].split('=', 1)
            assert algo == "sha256", "Unsupported hash algorithm"
            zipfile.set_expected_hash(filename, urlsafe_b64decode(binary(data)))
    
    
class VerifyingZipFile(zipfile.ZipFile):
    """ZipFile that can assert that each of its extracted contents matches
    an expected sha256 hash. Note that each file must be completly read in 
    order for its hash to be checked."""
    
    def __init__(self, file, mode="r", 
                 compression=zipfile.ZIP_STORED, 
                 allowZip64=False):
        zipfile.ZipFile.__init__(self, file, mode, compression, allowZip64)

        self.strict = False
        self._expected_hashes = {}
        self._hash_algorithm = hashlib.sha256
        
    def set_expected_hash(self, name, hash):
        """
        :param name: name of zip entry
        :param hash: bytes of hash (or None for "don't care")
        """
        self._expected_hashes[name] = hash
        
    def open(self, name_or_info, mode="r", pwd=None):
        """Return file-like object for 'name'."""
        # A non-monkey-patched version would contain most of zipfile.py
        ef = zipfile.ZipFile.open(self, name_or_info, mode, pwd)
        if isinstance(name_or_info, zipfile.ZipInfo):
            name = name_or_info.filename
        else:
            name = name_or_info
        if (name in self._expected_hashes 
            and self._expected_hashes[name] != None):
            expected_hash = self._expected_hashes[name]
            _update_crc_orig = ef._update_crc
            running_hash = self._hash_algorithm()
            def _update_crc(newdata, eof):
                _update_crc_orig(newdata, eof)
                running_hash.update(newdata)
                if eof and running_hash.digest() != expected_hash:
                    raise BadWheelFile("Bad hash for file %r" % ef.name)
            ef._update_crc = _update_crc
        elif self.strict and name not in self._expected_hashes:
            raise BadWheelFile("No expected hash for file %r" % ef.name)
        return ef

    def pop(self):
        """Truncate the last file off this zipfile.
        Assumes infolist() is in the same order as the files (true for
        ordinary zip files created by Python)"""
        if not self.fp:
            raise RuntimeError(
                  "Attempt to pop from ZIP archive that was already closed")
        last = self.infolist().pop()
        del self.NameToInfo[last.filename]
        self.fp.seek(last.header_offset, os.SEEK_SET)
        self.fp.truncate()
        self._didModify = True

def pick_best(candidates, supported, top=True):
    '''Pick the best supported wheel among the candidates.

    The algorithm ranks each candidate wheel with respect to the supported
    ones. A list of supported tags can be automatically generated with
    :func:`wheel.util.generate_supported`.

    :param candidates: A list of wheels that can be installed.
    :param supported: A list of tags which represent wheels that can be
        installed on the current system. Each tag is as follows::

            (python_implementation, abi, architecture)

        For example: ``('cp27', 'cp27m', 'linux_i686')``.
    :param top: If True, only return the best wheel. Otherwise return all the
        wheels among the candidates which are supported, sorted from best to
        worst.
    '''
    ranked = []
    for whl in candidates:
        try:
            preference, arity = whl.compatibility_rank(supported)
        except ValueError:  # When preferences is empty
            continue
        ranked.append((preference, arity, whl))
    if top:
        return min(ranked)
    return sorted(ranked)


def install(wheel_path):
    """Install a single wheel (.whl) file without regard for dependencies."""
    try:
        sys.real_prefix
    except AttributeError:
        raise Exception(
            "This alpha version of wheel will only install into a virtualenv")
    wf = WheelFile(wheel_path)
    raise NotImplementedError()
