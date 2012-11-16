Wheel
=====

A built-package format for Python.

A wheel is a ZIP-format archive with a specially formatted filename
and the .whl extension. It is designed to contain all the files for a
PEP 376 compatible install in a way that is very close to the on-disk
format. Many packages will be properly installed with only the "Unpack"
step (simply extracting the file onto sys.path), and the unpacked archive
preserves enough information to "Spread" (copy data and scripts to their
final locations) at any later time.

The wheel project provides a `bdist_wheel` command for setuptools
(requires distribute >= 0.6.28). Wheel files can be installed with a
patched `pip` from https://github.com/qwcode/pip or with wheel's own
command line utility.

The wheel documentation is at http://wheel.rtfd.org/. The
file format is documented in the draft PEP 427
(http://www.python.org/dev/peps/pep-0427/).

Why not egg?
------------

Python's egg format predates the packaging related standards we have today,
the most important being PEP 376 "Database of Installed Python Distributions"
which specifies the .dist-info directory (instead of .egg-info) and PEP 345 
"Metadata for Python Software Packages 1.2" which specifies how to express
dependencies (instead of requires.txt in .egg-info).

Wheel implements these things. It also provides a richer file naming
convention that communicates the Python implementation and ABI as well as
simply the language version used in a particular package.

Unlike .egg, wheel will be a fully-documented standard at the binary level
that is truly easy to install even if you do not want to use the reference
implementation.

