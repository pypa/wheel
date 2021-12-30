The Story of Wheel
==================

I was impressed with Tarek’s packaging talk at PyCon 2010, and I
admire PEP 345 (Metadata for Python Software Packages 1.2) and PEP 376
(Database of Installed Python Distributions) which standardize a richer
metadata format and show how distributions should be installed on disk. So
naturally with all the hubbub about ``packaging`` in Python 3.3, I decided
to try it to reap the benefits of a more standardized and predictable
Python packaging experience.

I began by converting ``cryptacular``, a password hashing package which
has a simple C extension, to use ``setup.cfg``. I downloaded the Python 3.3
source, struggled with the difference between ``setup.py`` and ``setup.cfg``
syntax, fixed the ``define_macros`` feature, stopped using the missing
``extras`` functionality, and several hours later I was able to generate my
``METADATA`` from ``setup.cfg``. I rejoiced at my newfound freedom from the
tyranny of arbitrary code execution during the build and install process.

It was a lot of work. The package is worse off than before, and it can’t
be built or installed without patching the Python source code itself.

It was about that time that distutils-sig had a discussion about the
need to include a generated ``setup.cfg`` from ``setup.cfg`` because
``setup.cfg`` wasn’t static enough. Wait, what?

Of course there is a different way to massively simplify the install
process. It’s called built or binary packages. You never have to run
``setup.py`` because there is no ``setup.py``. There is only METADATA aka
PKG-INFO. Installation has two steps: ‘build package’; ‘install
package’, and you can skip the first step, have someone else do it
for you, do it on another machine, or install the build system from a
binary package and let the build system handle the building. The build
is still complicated, but installation is simple.

With the binary package strategy people who want to install use a simple,
compatible installer, and people who want to package use whatever is
convenient for them for as long as it meets their needs. No one has
to rewrite ``setup.py`` for their own or the 20k+ other packages on PyPI
unless a different build system does a better job.

Wheel is my attempt to benefit from the excellent distutils-sig work
without having to fix the intractable ``distutils`` software itself. Like
``METADATA`` and ``.dist-info`` directories but unlike Extension(), it’s
simple enough that there really could be alternate implementations; the
simplest (but less than ideal) installer is nothing more than “unzip
archive.whl” somewhere on sys.path.

If you’ve made it this far you probably wonder whether I’ve heard
of eggs. Some comparisons:

* Wheel is an installation format; egg is importable. Wheel archives do not need to include .pyc and are less tied to a specific Python version or implementation. Wheel can install (pure Python) packages built with previous versions of Python so you don’t always have to wait for the packager to catch up.

* Wheel uses .dist-info directories; egg uses .egg-info. Wheel is compatible with the new world of Python ``packaging`` and the new concepts it brings.

* Wheel has a richer file naming convention for today’s multi-implementation world. A single wheel archive can indicate its compatibility with a number of Python language versions and implementations, ABIs, and system architectures. Historically the ABI has been specific to a CPython release, but when we get a longer-term ABI, wheel will be ready.

* Wheel is lossless. The first wheel implementation ``bdist_wheel`` always generates ``egg-info``, and then converts it to a ``.whl``. Later tools will allow for the conversion of existing eggs and bdist_wininst distributions.

* Wheel is versioned. Every wheel file contains the version of the wheel specification and the implementation that packaged it. Hopefully the next migration can simply be to Wheel 2.0.

I hope you will benefit from wheel.
