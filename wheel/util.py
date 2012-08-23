"""Utility functions."""

import sys
import base64
import json
try:
    import sysconfig
except ImportError:  # pragma nocover
    # Python < 2.7
    import distutils.sysconfig as sysconfig
from distutils.util import get_platform

__all__ = ['urlsafe_b64encode', 'urlsafe_b64decode', 'utf8', 'to_json',
           'from_json', 'generate_supported', 'get_abbr_impl', 'get_impl_ver']


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
    unicode
    def native(s):
        return s
    def binary(s):
        if isinstance(s, unicode):
            return s.encode('latin1')
        return s
except NameError:
    def native(s):
        if isinstance(s, bytes):
            return s.decode('latin1')
        return s
    def binary(s):
        if isinstance(s, str):
            return s.encode('latin1')


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
