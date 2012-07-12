"""Install a wheel
"""
# XXX see patched pip to install

import sys
import os.path
import re
import zipfile
import json
import hmac
import hashlib
from email.parser import Parser

from verlib import NormalizedVersion

from .decorator import reify
from .util import urlsafe_b64encode, utf8, to_json

# The next major version after this version of the 'wheel' tool:
VERSION_TOO_HIGH = NormalizedVersion("1.0")

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
        period-delimited tags in its filename. To choose a wheel file among
        several candidates having the same distribution version 'ver', an 
        installer ranks each triple of (pyver, abi, plat) that its Python 
        installation can run, sorting the wheels by the best-ranked tag it
        supports and then by their arity which is just 
        len(list(compatibility_tags))."""
        tags = self.parsed_filename.groupdict()
        for pyver in tags['pyver'].split('.'):
            for abi in tags['abi'].split('.'):
                for plat in tags['plat'].split('.'):
                    yield (pyver, abi, plat)
                    
    @property
    def arity(self):
        return len(list(self.compatibility_tags))

    @reify
    def parsed_wheel_info(self):
        """Parse wheel metadata"""
        return Parser().parse(self.zipfile.open(self.wheelinfo_name))    
        
    def check_version(self):
        version = self.parsed_wheel_info['Wheel-Version']
        assert NormalizedVersion(version) < VERSION_TOO_HIGH, "Wheel version is too high"
        
    def sign(self, key, alg="HS256"):
        """Sign the wheel file's RECORD using `key` and algorithm `alg`. Alg 
        values are from JSON Web Signatures; only HS256 is supported at this
        time."""
        if alg != 'HS256':
            # python-jws (not in pypi) supports other algorithms 
            raise ValueError("Unsupported algorithm")
        sig = self.sign_hs256(key)
        self.zipfile.writestr('/'.join((self.distinfo_name, 'RECORD.JWT')),
                              sig)
        
    def sign_hs256(self, key):
        record = self.zipfile.read('/'.join((self.distinfo_name, 'RECORD')))        
        record_digest = urlsafe_b64encode(hashlib.sha256(record).digest())
        header = utf8(to_json(dict(alg="HS256", typ="JWT")))
        payload = utf8(to_json(dict(hash="sha256="+record_digest)))
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
        
def install(wheel_path):
    """Install a single wheel (.whl) file without regard for dependencies."""
    try:
        sys.real_prefix
    except AttributeError:
        raise Exception("This alpha version of wheel will only install into a virtualenv")
    wf = WheelFile(wheel_path)
    
