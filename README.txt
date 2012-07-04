
wheel
=====

A built-package package format for Python.

Can be installed with a patched version of pip from
https://github.com/dholth/pip

Requires a patched distribute from https://bitbucket.org/dholth/distribute

Work on the spec is at https://docs.google.com/document/d/1mWPyvoeiqCrAy4UPNnvaz7Cgrqm4s_cfaTauAeJWABI/edit

Why not egg?
============

Python's egg format predates the packging related standards we have today,
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
