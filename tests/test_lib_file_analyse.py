import os
from wheel.lib_file_analyse import extract_macosx_min_system_version


def test_read_from_dynlib():
    dirname = os.path.dirname(__file__)
    dylib_dir = os.path.join(dirname, "testdata",
                             "macos_minimal_system_version")
    versions = [
        ("test_lib_10_6_fat.dynlib", "10.6"),
        ("test_lib_10_10_fat.dynlib", "10.10"),
        ("test_lib_10_14_fat.dynlib", "10.14"),
        ("test_lib_10_6.dynlib", "10.6"),
        ("test_lib_10_10.dynlib", "10.10"),
        ("test_lib_10_14.dynlib", "10.14"),
        ("test_lib_10_6_386.dynlib", "10.6"),
        ("test_lib_10_10_386.dynlib", "10.10"),
        ("test_lib_10_14_386.dynlib", "10.14"),
        ("test_lib_multiple_fat.dynlib", "10.14")
    ]
    for file_name, ver in versions:
        extracted = extract_macosx_min_system_version(
            os.path.join(dylib_dir, file_name)
        )
        str_ver = str(extracted[0]) + "." + str(extracted[1])
        assert str_ver == ver
        assert extract_macosx_min_system_version(
            os.path.join(dylib_dir, "test_lib.c")
        ) is None
