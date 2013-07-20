import os.path, sys, codecs, re

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = codecs.open(os.path.join(here, 'README.txt'), encoding='utf8').read()
CHANGES = codecs.open(os.path.join(here, 'CHANGES.txt'), encoding='utf8').read()

with codecs.open(os.path.join(os.path.dirname(__file__), 'wheel', '__init__.py'), 
                 encoding='utf8') as version_file:
    metadata = dict(re.findall(r"""__([a-z]+)__ = "([^"]+)""", version_file.read()))

#
# All these requirements are overridden by setup.cfg when wheel is built
# as a wheel:
#
signature_reqs = ['keyring']
if sys.platform != 'win32':
    signature_reqs.append('dirspec')
install_requires = []
if sys.version_info[:2] < (2, 7):
    install_requires.append('argparse')

setup(name='wheel',
      version=metadata['version'],
      description='A built-package format for Python.',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        ],
      author='Daniel Holth',
      author_email='dholth@fastmail.fm',
      url='http://bitbucket.org/dholth/wheel/',
      keywords=['wheel', 'packaging'],
      license='MIT',
      packages=[
          'wheel', 
          'wheel.test', 
          'wheel.tool', 
          'wheel.signatures'
          ],
      install_requires=install_requires,
      extras_require={
          'signatures': signature_reqs,
          'faster-signatures': ['ed25519ll'], 
          'tool': []
          },
      tests_require=['jsonschema', 'pytest', 'coverage', 'pytest-cov'],
      include_package_data=True,
      zip_safe=False,
      entry_points = """\
[console_scripts]
wininst2wheel = wheel.wininst2wheel:main
egg2wheel = wheel.egg2wheel:main
wheel = wheel.tool:main

[distutils.commands]
bdist_wheel = wheel.bdist_wheel:bdist_wheel"""
      )

