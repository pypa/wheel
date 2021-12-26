from __future__ import annotations

import base64
import sys


def urlsafe_b64encode(data: bytes) -> bytes:
    """urlsafe_b64encode without padding"""
    return base64.urlsafe_b64encode(data).rstrip(b"=")


def urlsafe_b64decode(data: bytes) -> bytes:
    """urlsafe_b64decode without padding"""
    pad = b"=" * (4 - (len(data) & 3))
    return base64.urlsafe_b64decode(data + pad)


def log(msg: str, *, error: bool = False) -> None:
    stream = sys.stderr if error else sys.stdout
    try:
        print(msg, file=stream, flush=True)
    except UnicodeEncodeError:
        # emulate backslashreplace error handler
        encoding = stream.encoding
        msg = msg.encode(encoding, "backslashreplace").decode(encoding)
        print(msg, file=stream, flush=True)
