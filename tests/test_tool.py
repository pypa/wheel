from wheel import tool


def test_convert_egg(egg_paths, tmpdir):
    tool.convert(egg_paths, str(tmpdir), verbose=False)
    assert len(tmpdir.listdir()) == len(egg_paths)


def test_unpack(wheel_paths, tmpdir):
    """
    Make sure 'wheel unpack' works.
    This also verifies the integrity of our testing wheel files.
    """
    for wheel_path in wheel_paths:
        tool.unpack(wheel_path, str(tmpdir))
