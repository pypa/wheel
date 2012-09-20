"""Utility functions."""

import sys
import os
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
    return base64.urlsafe_b64encode(data).rstrip(binary('='))


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

def open_for_csv(name, mode):
    if sys.version_info[0] < 3:
        nl = {}
        bin = 'b'
    else:
        nl = { 'newline': '' }
        bin = ''
    return open(name, mode + bin, **nl)

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
    
    abis = []

    soabi = sysconfig.get_config_var('SOABI')
    if soabi and soabi.startswith('cpython-'):
        abis[0:0] = ['cp' + soabi.split('-', 1)[-1]]
 
    abi3s = set()
    import imp
    for suffix in imp.get_suffixes():
        if suffix[0].startswith('.abi'):
            abi3s.add(suffix[0].split('.', 2)[1])

    abis.extend(sorted(list(abi3s)))

    abis.append('none')

    arch = get_platform().replace('.', '_').replace('-', '_')
    
    # Current version, current API (built specifically for our Python):
    for abi in abis:
        supported.append(('%s%s' % (impl, versions[0]), abi, arch))
            
    # No abi / arch, but requires our implementation:
    for i, version in enumerate(versions):
        supported.append(('%s%s' % (impl, version), 'none', 'any'))
        if i == 0:
            # Tagged specifically as being cross-version compatible 
            # (with just the major version specified)
            supported.append(('%s%s' % (impl, versions[0][0]), 'none', 'any')) 
            
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

if sys.platform == 'win32':
    import ctypes, ctypes.wintypes
    # CSIDL_APPDATA for reference - not used here for compatibility with
    # dirspec, which uses LOCAL_APPDATA and COMMON_APPDATA in that order
    csidl = dict(CSIDL_APPDATA=26, CSIDL_LOCAL_APPDATA=28,
            CSIDL_COMMON_APPDATA=35)
    def get_path(name):
        SHGFP_TYPE_CURRENT = 0
        buf = ctypes.create_unicode_buffer(ctypes.wintypes.MAX_PATH)
        ctypes.windll.shell32.SHGetFolderPathW(0, csidl[name], 0, SHGFP_TYPE_CURRENT, buf)
        return buf.value

    def save_config_path(*resource):
        appdata = get_path("CSIDL_LOCAL_APPDATA")
        path = os.path.join(appdata, *resource)
        if not os.path.isdir(path):
            os.makedirs(path)
        return path
    def load_config_paths(*resource):
        ids = ["CSIDL_LOCAL_APPDATA", "CSIDL_COMMON_APPDATA"]
        for id in ids:
            base = get_path(id)
            path = os.path.join(base, *resource)
            if os.path.exists(path):
                yield path
else:
    def save_config_path(*resource):
        import dirspec.basedir
        return dirspec.basedir.save_config_path(*resource)
    def load_config_paths(*resource):
        import dirspec.basedir
        return dirspec.basedir.load_config_paths(*resource)

