# coding: utf-8
import os.path, codecs, re

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = codecs.open(os.path.join(here, 'README.rst'), encoding='utf8').read()
CHANGES = codecs.open(os.path.join(here, 'CHANGES.txt'), encoding='utf8').read()

with codecs.open(os.path.join(os.path.dirname(__file__), 'wheel', '__init__.py'),
                 encoding='utf8') as version_file:
    metadata = dict(re.findall(r"""__([a-z]+)__ = "([^"]+)""", version_file.read()))

setup(name='wheel',
      version=metadata['version'],
      description='A built-package format for Python.',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.2",
          "Programming Language :: Python :: 3.3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: Implementation :: CPython",
          "Programming Language :: Python :: Implementation :: PyPy",
      ],
      author='Daniel Holth',
      author_email='dholth@fastmail.fm',
      maintainer=u'Alex Grönholm',
      maintainer_email='alex.gronholm@nextday.fi',
      url='https://github.com/pypa/wheel',
      keywords=['wheel', 'packaging'],
      license='MIT',
      packages=[
          'wheel',
          'wheel.test',
          'wheel.tool',
          'wheel.signatures'
          ],
      extras_require={
          'signatures': ['keyring', 'keyrings.alt'],
          'signatures:sys_platform!="win32"': ['pyxdg'],
          'faster-signatures': ['ed25519ll'],
          'tool': []
          },
      tests_require=[
          'jsonschema',
          'pytest',
          'coverage',
          'pytest-cov',
      ],
      include_package_data=True,
      zip_safe=False,
      entry_points = {
          'console_scripts': [
              'wheel=wheel.tool:main'
              ],
          'distutils.commands': [
              'bdist_wheel=wheel.bdist_wheel:bdist_wheel'
              ]
          }
      )
