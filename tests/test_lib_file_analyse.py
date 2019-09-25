import os
from wheel.lib_file_analyse import extract_macosx_min_system_version
from wheel.pep425tags import get_platform


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


def test_get_platform_macos(mocker, capsys):
    print(mocker, mocker.patch, mocker.patch.mock_module)
    dirname = os.path.dirname(__file__)
    dylib_dir = os.path.join(dirname, "testdata",
                             "macos_minimal_system_version")
    with mocker.patch("distutils.util.get_platform", return_value="macosx-10.14-x86_64"):
        assert get_platform(dylib_dir) == "macosx_10_14_x86_64"
    with mocker.patch("distutils.util.get_platform", return_value="macosx-10.9-x86_64"):
        assert get_platform(dylib_dir) == "macosx_10_14_x86_64"
        captured = capsys.readouterr()
        assert "[WARNING] This wheel needs higher macosx version than" in captured.err
    with mocker.patch("distutils.util.get_platform", return_value="macosx-10.9-x86_64"):
        with mocker.patch("os.walk", return_value=[
                (dylib_dir, [], ["test_lib_10_6.dynlib", "test_lib_10_10_fat.dynlib"])]):
            assert get_platform(dylib_dir) == "macosx_10_10_x86_64"
            captured = capsys.readouterr()
            assert "[WARNING] This wheel needs higher macosx version than" in captured.err

        with mocker.patch("os.walk", return_value=[
                (dylib_dir, [], ["test_lib_10_6.dynlib", "test_lib_10_6_fat.dynlib"])]):
            assert get_platform(dylib_dir) == "macosx_10_9_x86_64"
            mocker.patch.dict('os.environ', {"MACOSX_DEPLOYMENT_TARGET": "10.10"})
            assert get_platform(dylib_dir) == "macosx_10_10_x86_64"

    mocker.stopall()
    with mocker.patch("distutils.util.get_platform", return_value="macosx-10.9-x86_64"):
        mocker.patch.dict('os.environ', {"MACOSX_DEPLOYMENT_TARGET": "10.8"})
        with mocker.patch("os.walk", return_value=[
                (dylib_dir, [], ["test_lib_10_6.dynlib", "test_lib_10_6_fat.dynlib"])]):
            assert get_platform(dylib_dir) == "macosx_10_9_x86_64"
            captured = capsys.readouterr()
            print("aa", captured.err)
            assert "[WARNING] MACOSX_DEPLOYMENT_TARGET is set to lower value" in captured.err
        with mocker.patch("os.walk", return_value=[
                (dylib_dir, [], ["test_lib_10_6.dynlib", "test_lib_10_10_fat.dynlib"])]):
            assert get_platform(dylib_dir) == "macosx_10_10_x86_64"
            captured = capsys.readouterr()
            print("aa", captured.err)
            assert "[WARNING] MACOSX_DEPLOYMENT_TARGET is set to lower value" in captured.err
    mocker.stopall()


def test_get_platform_linux(mocker):
    with mocker.patch("distutils.util.get_platform", return_value="linux_x86_64"):
        mocker.patch("sys.maxsize", new=2147483647)
        assert get_platform(None) == "linux_i686"
