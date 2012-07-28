"""Install a wheel
"""
# XXX see patched pip to install

import sys
import os.path
import re
import zipfile
import hmac
import hashlib
from email.parser import Parser

from wheel.decorator import reify
from wheel.util import urlsafe_b64encode, utf8, to_json

# The next major version after this version of the 'wheel' tool:
VERSION_TOO_HIGH = (1, 0)

# Non-greedy matching of an optional build number may be too clever (more
# invalid wheel filenames will match). Separate regex for .dist-info?
WHEEL_INFO_RE = re.compile(
    r"""^(?P<namever>(?P<name>.+?)(-(?P<ver>\d.+?))?)
    ((-(?P<build>\d.*?))?-(?P<pyver>.+?)-(?P<abi>.+?)-(?P<plat>.+?)
    \.whl|\.dist-info)$""",
    re.VERBOSE).match


class WheelFile(object):
    """Parse wheel-specific attributes from a wheel (.whl) file"""
    WHEEL_INFO = "WHEEL"

    def __init__(self, filename):
        self.filename = filename
        basename = os.path.basename(filename)
        self.parsed_filename = WHEEL_INFO_RE(basename)
        if not basename.endswith('.whl') or self.parsed_filename is None:
            raise ValueError("Bad filename '%s'" % filename)

    def __repr__(self):
        return self.filename

    @reify
    def zipfile(self):
        return zipfile.ZipFile(self.filename)

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

    def sign(self, key, alg="HS256"):
        """Sign the wheel file's RECORD using `key` and algorithm `alg`. Alg
        values are from JSON Web Signatures; only HS256 is supported at this
        time."""
        if alg != 'HS256':
            # python-jws (not in pypi) supports other algorithms
            raise ValueError("Unsupported algorithm")
        sig = self.sign_hs256(key)
        self.zipfile.writestr('/'.join((self.distinfo_name, 'RECORD.jws')),
                              sig)

    def sign_hs256(self, key):
        record = self.zipfile.read('/'.join((self.distinfo_name, 'RECORD')))
        record_digest = urlsafe_b64encode(hashlib.sha256(record).digest())
        header = utf8(to_json(dict(alg="HS256", typ="JWT")))
        payload = utf8(to_json(dict(hash="sha256=" + record_digest)))
        protected = b'.'.join((urlsafe_b64encode(header),
                               urlsafe_b64encode(payload)))
        mac = hmac.HMAC(key, protected, hashlib.sha256).digest()
        sig = b'.'.join((protected, urlsafe_b64encode(mac)))
        return sig

    def verify_hs256(self, key):
        signature = self.zipfile.read('/'.join((self.distinfo_name,
                                                'RECORD.JWT')))
        verify = self.sign_hs256(key)
        if verify != signature:
            return False
        return True


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
