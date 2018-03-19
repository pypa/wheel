from email.parser import Parser

from wheel.pkginfo import write_pkg_info


def test_pkginfo_mangle_from(tmpdir):
    """Test that write_pkginfo() will not prepend a ">" to a line starting with "From"."""
    metadata = """\
Metadata-Version: 2.1
Name: foo

From blahblah

====
Test
====

"""
    message = Parser().parsestr(metadata)
    pkginfo_file = tmpdir.join('PKGINFO')
    write_pkg_info(str(pkginfo_file), message)
    assert pkginfo_file.read_text('ascii') == metadata
