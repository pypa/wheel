# Convert egg-style metadata to Metadata 2.0, json version.

from collections import defaultdict
from .pkginfo import read_pkg_info
import re

METADATA_VERSION = "2.0"

PLURAL_FIELDS = { "classifier" : "classifiers", 
                  "provides_dist" : "provides",
                  "provides_extra" : "extras" }

SKIP_FIELDS = set()

CONTACT_FIELDS = (({"email":"author_email", "name": "author"}, 
                    "author"),
                  ({"email":"maintainer_email", "name": "maintainer"}, 
                    "maintainer"))

# commonly filled out as "UNKNOWN" by distutils:
UNKNOWN_FIELDS = set(("author", "author_email", "platform", "home_page", 
                      "license"))

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

def pkginfo_to_dict(path, distribution=None):
    """
    Convert PKG-INFO to a prototype Metadata 2.0 dict.
    
    path: path to PKG-INFO file
    distribution: optional distutils Distribution()
    """
    
    metadata = {}
    pkg_info = read_pkg_info(path)
    for key in unique(k.lower() for k in pkg_info.keys()):
        low_key = key.replace('-', '_')

        if low_key in SKIP_FIELDS: 
            continue
        
        if low_key in UNKNOWN_FIELDS and pkg_info.get(key) == 'UNKNOWN':
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

        elif low_key == 'provides_extra':
            if not 'extras' in metadata:
                metadata['extras'] = []
            metadata['extras'].extend(pkg_info.get_all(key))
            
                
        elif low_key == 'home_page':
            metadata['project_urls'] = [{'Home':pkg_info[key]}]

        else:
            metadata[low_key] = pkg_info[key]

    metadata['metadata_version'] = METADATA_VERSION
    
    # include extra information if distribution is available
    if distribution:
        for requires, attr in (('test_requires', 'tests_require'),):
            try:
                requirements = getattr(distribution, attr)
                if requirements:
                    metadata[requires] = requirements 
            except AttributeError:
                pass
            
    # handle contacts
    contacts = []
    for contact_type, role in CONTACT_FIELDS:
        contact = {}
        for key in contact_type:
            if contact_type[key] in metadata:
                contact[key] = metadata.pop(contact_type[key])
        if contact:
            contact['role'] = role
            contacts.append(contact)
    if contacts:
        metadata['contacts'] = contacts
        
    return metadata

if __name__ == "__main__":
    import sys, pprint
    pprint.pprint(pkginfo_to_dict(sys.argv[1]))
