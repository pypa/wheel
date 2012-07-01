"""Install a wheel
"""
# XXX see patched pip

"""
setup.cfg categories

    config
    appdata
    appdata.arch
    appdata.persistent
    appdata.disposable
    help
    icon
    scripts
    doc
    info
    man    
    
    plus purelib, platlib, ...
"""

import sys
import os.path
import re
import zipfile
from email.parser import Parser

from verlib import NormalizedVersion

from .decorator import reify

# The next major version after this version of the 'wheel' tool:
VERSION_TOO_HIGH = NormalizedVersion("1.0")

WHEEL_NAME = re.compile(
    r"""(?P<namever>(?P<name>.+)-(?P<ver>.+))
    (-(?P<pyver>.+)-(?P<abi>.+)-(?P<plat>.+)\.whl|\.dist-info)$""",
    re.VERBOSE
).match

class WheelFile(object):
    """Parse wheel-specific attributes from a wheel (.whl) file"""    
    WHEEL_INFO = "WHEEL"
    
    def __init__(self, filename):
        self.filename = filename
        basename = os.path.basename(filename)
        self.parsed_filename = WHEEL_NAME(basename)
        if not basename.endswith('.whl') or self.parsed_filename is None:
            raise ValueError("Bad filename '%s'" % filename)
        self.zipfile = zipfile.ZipFile(filename)
        
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
            
    @reify
    def parsed_wheel_info(self):
        """Parse wheel metadata"""
        return Parser().parse(self.zipfile.open(self.wheelinfo_name))
        
    def check_version(self):
        version = self.parsed_wheel_info['Wheel-Version']
        assert NormalizedVersion(version) < VERSION_TOO_HIGH, "Wheel version is too high"

def install(wheel_path):
    """Install a single wheel (.whl) file without regard for dependencies."""
    try:
        sys.real_prefix
    except AttributeError:
        raise Exception("This alpha version of wheel will only install into a virtualenv")
    wf = WheelFile(wheel_path)
    
