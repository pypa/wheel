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
