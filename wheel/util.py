import base64
import hashlib
import json
import sys

__all__ = ['urlsafe_b64encode', 'urlsafe_b64decode', 'utf8',
           'to_json', 'from_json', 'matches_requirement']


if sys.version_info[0] < 3:
    text_type = unicode  # noqa: F821

    def native(s, encoding='ascii'):
        return s
else:
    text_type = str

    def native(s, encoding='ascii'):
        if isinstance(s, bytes):
            return s.decode(encoding)
        return s


def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(binary('='))


def urlsafe_b64decode(data):
    """urlsafe_b64decode without padding"""
    pad = b'=' * (4 - (len(data) & 3))
    return base64.urlsafe_b64decode(data + pad)


def to_json(o):
    """Convert given data to JSON."""
    return json.dumps(o, sort_keys=True)


def from_json(j):
    """Decode a JSON payload."""
    return json.loads(j)


def open_for_csv(name, mode):
    if sys.version_info[0] < 3:
        kwargs = {}
        mode += 'b'
    else:
        kwargs = {'newline': '', 'encoding': 'utf-8'}

    return open(name, mode, **kwargs)


def utf8(data):
    """Utf-8 encode data."""
    if isinstance(data, text_type):
        return data.encode('utf-8')
    return data


def binary(s):
    if isinstance(s, text_type):
        return s.encode('ascii')
    return s


class HashingFile(object):
    def __init__(self, path, mode, hashtype='sha256'):
        self.fd = open(path, mode)
        self.hashtype = hashtype
        self.hash = hashlib.new(hashtype)
        self.length = 0

    def write(self, data):
        self.hash.update(data)
        self.length += len(data)
        self.fd.write(data)

    def close(self):
        self.fd.close()

    def digest(self):
        if self.hashtype == 'md5':
            return self.hash.hexdigest()
        digest = self.hash.digest()
        return self.hashtype + '=' + native(urlsafe_b64encode(digest))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fd.close()


def matches_requirement(req, wheels):
    """List of wheels matching a requirement.

    :param req: The requirement to satisfy
    :param wheels: List of wheels to search.
    """
    try:
        from pkg_resources import Distribution, Requirement
    except ImportError:
        raise RuntimeError("Cannot use requirements without pkg_resources")

    req = Requirement.parse(req)

    selected = []
    for wf in wheels:
        f = wf.parsed_filename
        dist = Distribution(project_name=f.group("name"), version=f.group("ver"))
        if dist in req:
            selected.append(wf)
    return selected
