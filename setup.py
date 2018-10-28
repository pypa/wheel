# coding: utf-8
import os.path
import io
import re

from setuptools import setup, find_packages


here = os.path.abspath(os.path.dirname(__file__))


def readall(*args):
    with io.open(os.path.join(here, *args), encoding='utf8') as fp:
        return fp.read()


README = readall('README.rst')
metadata = dict(re.findall(r"""__([a-z]+)__ = "([^"]+)""", readall('wheel', '__init__.py')))

setup(name='wheel',
      version=metadata['version'],
      description='A built-package format for Python.',
      long_description=README,
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "Topic :: System :: Archiving :: Packaging",
          "License :: OSI Approved :: MIT License",
          "Programming Language :: Python",
          "Programming Language :: Python :: 2",
          "Programming Language :: Python :: 2.7",
          "Programming Language :: Python :: 3",
          "Programming Language :: Python :: 3.4",
          "Programming Language :: Python :: 3.5",
          "Programming Language :: Python :: 3.6",
          "Programming Language :: Python :: 3.7"
      ],
      author='Daniel Holth',
      author_email='dholth@fastmail.fm',
      maintainer=u'Alex Grönholm',
      maintainer_email='alex.gronholm@nextday.fi',
      url='https://github.com/pypa/wheel',
      project_urls={
          'Documentation': 'https://wheel.readthedocs.io/',
          'Changelog': 'https://wheel.readthedocs.io/en/stable/news.html',
          'Issue Tracker': 'https://github.com/pypa/wheel/issues'
      },
      keywords=['wheel', 'packaging'],
      license='MIT',
      packages=find_packages(),
      python_requires=">=2.7, !=3.0.*, !=3.1.*, !=3.2.*, !=3.3.*",
      extras_require={
          'test': ['pytest >= 3.0.0', 'pytest-cov']
          },
      include_package_data=True,
      zip_safe=False,
      entry_points={
          'console_scripts': [
              'wheel=wheel.cli:main'
              ],
          'distutils.commands': [
              'bdist_wheel=wheel.bdist_wheel:bdist_wheel'
              ]
          }
      )
