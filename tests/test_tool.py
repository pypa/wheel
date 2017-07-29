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


def test_keygen():
    def get_keyring():
        WheelKeys, keyring = tool.get_keyring()

        class WheelKeysTest(WheelKeys):
            def save(self):
                pass

        class keyringTest:
            @classmethod
            def get_keyring(cls):
                class keyringTest2:
                    pw = None

                    def set_password(self, a, b, c):
                        self.pw = c

                    def get_password(self, a, b):
                        return self.pw

                return keyringTest2()

        return WheelKeysTest, keyringTest

    tool.keygen(get_keyring=get_keyring)
