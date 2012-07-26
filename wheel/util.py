"""Utility functions."""

import re
import sys
import base64
import json
import sysconfig
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
    return json.dumps(o, sort_keys=True)


def from_json(j):
    return json.loads(j)


try:
    unicode

    def utf8(data):
        if isinstance(data, unicode):
            return data.encode('utf-8')
        return data
except NameError:
    def utf8(data):
        if isinstance(data, str):
            return data.encode('utf-8')
        return data


def get_abbr_impl():
    """Return abbreviated implementation name"""
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
    impl_ver = sysconfig.get_config_var("py_version_nodot")
    if not impl_ver:
        impl_ver = ''.join(map(str, sys.version_info[:2]))
    return impl_ver


def generate_supported(versions=None):
    # XXX: Only a draft
    supported = []
    current_ver = get_impl_ver()
    # Versions must be given with respect to the preference
    if versions is None:
        versions = [''.join(map(str, sys.version_info[:2]))]
    impl = get_abbr_impl()
    abis = ['noabi']  # XXX: Fix here
    arch = get_platform().replace('.', '_').replace('-', '_')
    for version in versions:
        for abi in abis:
            supported.append(('%s%s' % (impl, version), abi, arch))
        if not impl.startswith('py'):
            # Add pure Python distributions if not already done so
            supported.append(('py%s' % (version), 'noabi', 'noarch'))
    return supported
