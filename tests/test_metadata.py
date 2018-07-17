from wheel.metadata import generate_requirements
from wheel.metadata import pkginfo_to_metadata


def test_generate_requirements():
    extras_require = {
        'test': ['ipykernel', 'ipython', 'mock'],
        'test:python_version == "3.3"': ['pytest<3.3.0'],
        'test:python_version >= "3.4" or python_version == "2.7"': ['pytest'],
    }
    expected_metadata = [
        ('Provides-Extra',
         'test'),
        ('Requires-Dist',
         "ipykernel; extra == 'test'"),
        ('Requires-Dist',
         "ipython; extra == 'test'"),
        ('Requires-Dist',
         "mock; extra == 'test'"),
        ('Requires-Dist',
         'pytest (<3.3.0); (python_version == "3.3") and extra == \'test\''),
        ('Requires-Dist',
         'pytest; (python_version >= "3.4" or python_version == "2.7") and extra == \'test\''),
    ]
    generated_metadata = sorted(generate_requirements(extras_require))
    assert generated_metadata == expected_metadata


def test_generate_requirements_no_duplicate_extras():
    extras_require = {
        'signatures': ['keyring', 'keyrings.alt'],
        'signatures:sys_platform!="win32"': ['pyxdg'],
        'faster-signatures': ['ed25519ll'],
        'test': ['pytest >= 3.0.0', 'pytest-cov']
    }
    expected_metadata = [
        ('Provides-Extra', 'faster-signatures'),
        ('Provides-Extra', 'signatures'),
        ('Provides-Extra', 'test'),
        ('Requires-Dist', "ed25519ll; extra == 'faster-signatures'"),
        ('Requires-Dist', "keyring; extra == 'signatures'"),
        ('Requires-Dist', "keyrings.alt; extra == 'signatures'"),
        ('Requires-Dist', "pytest (>=3.0.0); extra == 'test'"),
        ('Requires-Dist', "pytest-cov; extra == 'test'"),
        ('Requires-Dist',
         'pyxdg; (sys_platform!="win32") and extra == \'signatures\''),
    ]
    generated_metadata = sorted(generate_requirements(extras_require))
    assert generated_metadata == expected_metadata


def test_pkginfo_to_metadata_no_duplicate_extras(tmpdir):
    pkg_info = tmpdir.join('PKG-INFO')
    pkg_info.write_binary(b'Metadata-Version: 0.0\nName: name\nVersion: 0.1\nProvides-Extra: test\n')
    egg_info_dir = tmpdir.ensure_dir('test.egg-info')
    requires_file = egg_info_dir.join('requires.txt')
    requires_file.write_binary(b'[test]\n')
    message = pkginfo_to_metadata(egg_info_path=str(egg_info_dir), pkginfo_path=str(pkg_info))
    assert message.items() == [
        ('Metadata-Version', '2.1'),
        ('Name', 'name'),
        ('Version', '0.1'),
        ('Provides-Extra', 'test'),
    ]
