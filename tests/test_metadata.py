from wheel.metadata import generate_requirements


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
