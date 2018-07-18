from wheel.metadata import pkginfo_to_metadata


def test_pkginfo_to_metadata(tmpdir):
    expected_metadata = [
        ('Metadata-Version', '2.1'),
        ('Name', 'spam'),
        ('Version', '0.1'),
        ('Provides-Extra', 'test'),
        ('Provides-Extra', 'signatures'),
        ('Provides-Extra', 'faster-signatures'),
        ('Requires-Dist', "ed25519ll; extra == 'faster-signatures'"),
        ('Requires-Dist', "keyring; extra == 'signatures'"),
        ('Requires-Dist', "keyrings.alt; extra == 'signatures'"),
        ('Requires-Dist', 'pyxdg; (sys_platform!="win32") and extra == \'signatures\''),
        ('Requires-Dist', "pytest (>=3.0.0); extra == 'test'"),
        ('Requires-Dist', "pytest-cov; extra == 'test'"),
    ]

    pkg_info = tmpdir.join('PKG-INFO')
    pkg_info.write("""\
Metadata-Version: 0.0
Name: spam
Version: 0.1
Provides-Extra: test
Provides-Extra: signatures
Provides-Extra: faster-signatures""")

    egg_info_dir = tmpdir.ensure_dir('test.egg-info')
    egg_info_dir.join('requires.txt').write("""\
[faster-signatures]
ed25519ll

[signatures]
keyring
keyrings.alt

[signatures:sys_platform!="win32"]
pyxdg

[test]
pytest>=3.0.0
pytest-cov""")

    message = pkginfo_to_metadata(egg_info_path=str(egg_info_dir), pkginfo_path=str(pkg_info))
    assert message.items() == expected_metadata
