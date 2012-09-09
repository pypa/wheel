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
    supported = []
    
    # Versions must be given with respect to the preference
    if versions is None:
        versions = []
        major = sys.version_info[0]
        # Support all previous minor Python versions.
        for minor in range(sys.version_info[1], -1, -1):
            versions.append(''.join(map(str, (major, minor))))
            
    impl = get_abbr_impl()
    
    abis = ['none']
    
    soabi = sysconfig.get_config_var('SOABI')
    if soabi and soabi.startswith('cpython-'):
        abis[0:0] = ['cp' + soabi.split('-', 1)[-1]]
    
    arch = get_platform().replace('.', '_').replace('-', '_')
    
    # Current version, current API (built specifically for our Python):
    for abi in abis:
        supported.append(('%s%s' % (impl, versions[0]), abi, arch))
        
    # Tagged specifically as being cross-version compatible 
    # (with just the major version specified)
    supported.append(('%s%s' % (impl, versions[0][0]), 'none', 'any')) 
    
    # No abi / arch, but requires our implementation:
    for version in versions[1:]:
        supported.append(('%s%s' % (impl, version), 'none', 'any'))
    
    # No abi / arch, generic Python
    for i, version in enumerate(versions):
        supported.append(('py%s' % (version,), 'none', 'any'))
        if i == 0:
            supported.append(('py%s' % (version[0]), 'none', 'any'))
        
    return supported


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
