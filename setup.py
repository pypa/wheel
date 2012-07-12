import os

from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
README = open(os.path.join(here, 'README.txt')).read()
CHANGES = open(os.path.join(here, 'CHANGES.txt')).read()

setup(name='wheel',
      version='0.4.1',
      description='A built-package format for Python.',
      long_description=README + '\n\n' +  CHANGES,
      classifiers=[
        "Development Status :: 2 - Pre-Alpha",
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
      keywords='wheel packaging',
      license='MIT',
      packages=['wheel'],
      install_requires=['distribute', 'verlib', 'markerlib'],
      include_package_data=True,
      zip_safe=False,
      test_suite = 'nose.collector',
      entry_points = open(os.path.join(here, 'entry_points.txt')).read()
      )

