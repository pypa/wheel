# Convert egg-style metadata to Metadata 2.0, json version.
# This is currently based on the pypi json API but with less UNKNOWN.

from collections import defaultdict
from .pkginfo import read_pkg_info
import re

METADATA_VERSION = "2.0"
PLURAL_FIELDS = { "classifier" : "classifiers", 
                  "provides_dist" : "provides",
                  "provides_extra" : "extras" }
SKIP_FIELDS = set(["description"])

# Will only support markers-as-extras here. Wheel itself is probably
# the only program that uses non-extras markers in METADATA/PKG-INFO.
EXTRA_RE = re.compile("extra == '(?P<extra>.+)'")
KEYWORDS_RE = re.compile("[\0-,]+")

def unique(iterable):
    seen = set()
    for value in iterable:
        if not value in seen:
            seen.add(value)
            yield value

def pkginfo_to_dict(path):
    """Convert a PKG-INFO file to a prototype Metadata 2.0 dict."""
    metadata = {}
    pkg_info = read_pkg_info(path)
    for key in unique(k.lower() for k in pkg_info.keys()):
        low_key = key.replace('-', '_')

        if low_key in SKIP_FIELDS: 
            continue

        if low_key in PLURAL_FIELDS:
            metadata[PLURAL_FIELDS[low_key]] = pkg_info.get_all(key)

        elif low_key == "requires_dist":
            requirements = []
            extra_requirements = defaultdict(list)
            for requirement, sep, marker in (value.partition(';') 
                                        for value in pkg_info.get_all(key)):
                marker = marker.strip()
                if marker:
                    extra_match = EXTRA_RE.match(marker)
                    if extra_match:
                        extra_name = extra_match.group('extra')
                        extra_requirements[extra_name].append(requirement)
                else:
                    requirements.append(requirement)
            metadata['requires'] = requirements
            if extra_requirements:
                metadata['may_require'] = [{'extra':key, 'dependencies':value} 
                        for key, value in sorted(extra_requirements.items())]
                metadata['extras'] = [key for key in sorted(extra_requirements.keys())]

        elif low_key == 'provides-extra':
            if not 'extras' in metadata:
                metadata['extras'] = []
            metadata['extras'].extend(pkg_info.get_all(key))

        else:
            metadata[low_key] = pkg_info[key]

    metadata['metadata_version'] = METADATA_VERSION
    return metadata

if __name__ == "__main__":
    import sys, pprint
    pprint.pprint(pkginfo_to_dict(sys.argv[1]))
    
#    {
#        "maintainer": null, 
#        "docs_url": "", 
#        "requires_python": null, 
#        "maintainer_email": null, 
#        "cheesecake_code_kwalitee_id": null, 
#        "keywords": "wheel packaging", 
#        "package_url": "http://pypi.python.org/pypi/wheel", 
#        "author": "Daniel Holth", 
#        "author_email": "dholth@fastmail.fm", 
#        "download_url": "UNKNOWN", 
#        "platform": "UNKNOWN", 
#        "version": "1.0.0a1", 
#        "cheesecake_documentation_id": null, 
#        "_pypi_hidden": false, 
#        "description": "Blah blah blah blah", 
#        "release_url": "http://pypi.python.org/pypi/wheel/1.0.0a1", 
#        "_pypi_ordering": 128, 
#        "classifiers": [
#            "Development Status :: 4 - Beta", 
#            "Intended Audience :: Developers", 
#            "Programming Language :: Python", 
#            "Programming Language :: Python :: 2", 
#            "Programming Language :: Python :: 2.6", 
#            "Programming Language :: Python :: 2.7", 
#            "Programming Language :: Python :: 3", 
#            "Programming Language :: Python :: 3.2", 
#            "Programming Language :: Python :: 3.3"
#        ], 
#        "bugtrack_url": "", 
#        "name": "wheel", 
#        "license": "MIT", 
#        "summary": "A built-package format for Python.", 
#        "home_page": "http://bitbucket.org/dholth/wheel/", 
#        "stable_version": null, 
#        "cheesecake_installability_id": null
#    }, 
