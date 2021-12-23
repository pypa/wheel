import base64


def native(s, encoding="utf-8"):
    if isinstance(s, bytes):
        return s.decode(encoding)
    else:
        return s


def urlsafe_b64encode(data):
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def urlsafe_b64decode(data):
    """urlsafe_b64decode without padding"""
    pad = b"=" * (4 - (len(data) & 3))
    return base64.urlsafe_b64decode(data + pad)


def as_unicode(s):
    if isinstance(s, bytes):
        return s.decode("utf-8")
    return s


def as_bytes(s):
    if isinstance(s, str):
        return s.encode("utf-8")
    else:
        return s
