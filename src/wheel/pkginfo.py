"""Tools for reading and writing PKG-INFO / METADATA without caring
about the encoding."""

from email.generator import BytesGenerator
from email.parser import Parser


def read_pkg_info_bytes(bytestr):
    headers = bytestr.decode(encoding="ascii", errors="surrogateescape")
    message = Parser().parsestr(headers)
    return message


def read_pkg_info(path):
    with open(path, encoding="ascii", errors="surrogateescape") as headers:
        message = Parser().parse(headers)

    return message


def write_pkg_info(path, message):
    with open(path, "wb") as out:
        BytesGenerator(out, mangle_from_=False, maxheaderlen=0).flatten(message)
