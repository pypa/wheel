"""Utility functions."""

import re
import sys
import base64
import json
import sysconfig
from distutils.util import get_platform

__all__ = ['urlsafe_b64encode', 'urlsafe_b64decode', 'utf8', 
           'to_json', 'from_json', 'parse_version', 'generate_supported',
           'get_abbr_impl']

component_re = re.compile(r'(\d+ | [a-z]+ | \.| -)', re.VERBOSE)
replace = {'pre':'c', 'preview':'c','-':'final-','rc':'c','dev':'@'}.get


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
    
# Next two functions from distribute's pkg_resources.py

def _parse_version_parts(s):
    for part in component_re.split(s):
        part = replace(part,part)
        if part in ['', '.']:
            continue
        if part[:1] in '0123456789':
            yield part.zfill(8)    # pad for numeric comparison
        else:
            yield '*'+part

    yield '*final'  # ensure that alpha/beta/candidate are before final


def parse_version(s):
    """Convert a version string to a chronologically-sortable key

    This is a rough cross between distutils' StrictVersion and LooseVersion;
    if you give it versions that would work with StrictVersion, then it behaves
    the same; otherwise it acts like a slightly-smarter LooseVersion. It is
    *possible* to create pathological version coding schemes that will fool
    this parser, but they should be very rare in practice.

    The returned value will be a tuple of strings.  Numeric portions of the
    version are padded to 8 digits so they will compare numerically, but
    without relying on how numbers compare relative to strings.  Dots are
    dropped, but dashes are retained.  Trailing zeros between alpha segments
    or dashes are suppressed, so that e.g. "2.4.0" is considered the same as
    "2.4". Alphanumeric parts are lower-cased.

    The algorithm assumes that strings like "-" and any alpha string that
    alphabetically follows "final"  represents a "patch level".  So, "2.4-1"
    is assumed to be a branch or patch of "2.4", and therefore "2.4.1" is
    considered newer than "2.4-1", which in turn is newer than "2.4".

    Strings like "a", "b", "c", "alpha", "beta", "candidate" and so on (that
    come before "final" alphabetically) are assumed to be pre-release versions,
    so that the version "2.4" is considered newer than "2.4a1".

    Finally, to handle miscellaneous cases, the strings "pre", "preview", and
    "rc" are treated as if they were "c", i.e. as though they were release
    candidates, and therefore are not as new as a version string that does not
    contain them, and "dev" is replaced with an '@' so that it sorts lower than
    than any other pre-release tag.
    """
    parts = []
    for part in _parse_version_parts(s.lower()):
        if part.startswith('*'):
            # remove trailing zeros from each series of numeric parts
            while parts and parts[-1]=='00000000':
                parts.pop()
        parts.append(part)
    return tuple(parts)


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
