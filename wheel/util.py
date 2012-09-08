"""Utility functions."""

import sys
import base64
import json
import hashlib
try:
    import sysconfig
except ImportError:  # pragma nocover
    # Python < 2.7
    import distutils.sysconfig as sysconfig
from distutils.util import get_platform

__all__ = ['urlsafe_b64encode', 'urlsafe_b64decode', 'utf8', 'to_json',
           'from_json', 'generate_supported', 'get_abbr_impl', 'get_impl_ver',
           'compatibility_match']


def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b'=')


def urlsafe_b64decode(data):
    """urlsafe_b64decode without padding"""
    pad = b'=' * (4 - (len(data) & 3))
    return base64.urlsafe_b64decode(data + pad)


def to_json(o):
    '''Convert given data to JSON.'''
    return json.dumps(o, sort_keys=True)


def from_json(j):
    '''Decode a JSON payload.'''
    return json.loads(j)


try:
    unicode

    def utf8(data):
        '''Utf-8 encode data.'''
        if isinstance(data, unicode):
            return data.encode('utf-8')
        return data
except NameError:
    def utf8(data):
        '''Utf-8 encode data.'''
        if isinstance(data, str):
            return data.encode('utf-8')
        return data


try:
    # For encoding ascii back and forth between bytestrings, as is repeatedly
    # necessary in JSON-based crypto under Python 3
    unicode
    def native(s):
        return s
    def binary(s):
        if isinstance(s, unicode):
            return s.encode('ascii')
        return s
except NameError:
    def native(s):
        if isinstance(s, bytes):
            return s.decode('ascii')
        return s
    def binary(s):
        if isinstance(s, str):
            return s.encode('ascii')


def get_abbr_impl():
    """Return abbreviated implementation name."""
    if hasattr(sys, 'pypy_version_info'):
        pyimpl = 'pp'
    elif sys.platform.startswith('java'):
        pyimpl = 'jy'
    elif sys.platform == 'cli':
        pyimpl = 'ip'
    else:
        pyimpl = 'cp'
    return pyimpl


def get_impl_ver():
    '''Return implementation version.'''
    impl_ver = sysconfig.get_config_var("py_version_nodot")
    if not impl_ver:
        impl_ver = ''.join(map(str, sys.version_info[:2]))
    return impl_ver


def generate_supported(versions=None):
    '''Generate supported tags for each version specified in `versions`.

    Versions must be given with respect to preference from best to worst.
    If `versions` is None, then the current version is assumed.
    Returned tags are sorted from best-matching tags to worst. All tags
    returned should be compatible with the machine.
    '''
    # XXX: Only a draft
    supported = []
    current_ver = get_impl_ver()
    # Versions must be given with respect to the preference
    if versions is None:
        versions = [''.join(map(str, sys.version_info[:2]))]
    impl = get_abbr_impl()
    abis = ['none']  # XXX: Should add more depending on the implementation
    arch = get_platform().replace('.', '_').replace('-', '_')
    for version in versions:
        for abi in abis:
            supported.append(('%s%s' % (impl, version), abi, arch))
        if not impl.startswith('py'):
            # Add pure Python distributions if not already done so
            supported.append(('py%s' % (version), 'none', 'any'))
    return supported

def compatibility_match(declared, tag):
    dpyver, dabi, dplat = declared
    pyver, abi, plat = tag

    # Platform: declared 'any' or matches
    if dplat != 'any' and dplat != plat:
        return False
    # ABI: declared 'none' or matches
    if dabi != 'none' and dabi != abi:
        return False

    # Python version: Implementation must match unless declared as 'py'
    # (generic), major version must match, and if declared as for a specific
    # minor version this must match too.
    if dpyver[:2] != 'py' and dpyver[:2] != pyver[:2]:
        return False
    if dpyver[2] != pyver[2]:
        return False
    if len(dpyver) > 3 and dpyver[3] != pyver[3]:
        return False
    return True

class HashingFile(object):
    def __init__(self, fd, hashtype='sha256'):
        self.fd = fd
        self.hashtype = hashtype
        self.hash = hashlib.new(hashtype)
        self.length = 0
    def read(self, n):
        data = self.fd.read(n)
        self.hash.update(data)
        self.length += len(data)
        return data
    def close(self):
        self.fd.close()
    def digest(self):
        if self.hashtype == 'md5':
            return self.hash.hexdigest()
        digest = self.hash.digest()
        return self.hashtype + '=' + native(urlsafe_b64encode(digest))
