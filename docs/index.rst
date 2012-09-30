.. wheel documentation master file, created by
   sphinx-quickstart on Thu Jul 12 00:14:09 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Wheel
=====

A built-package format for Python.

A wheel is a ZIP-format archive with a specially formatted filename and
the .whl extension. It is designed to contain all the files for a PEP 376
compatible install in a way that is very close to the on-disk format. Many
packages will be properly installed with only the “Unpack” step
(simply extracting the file onto sys.path), and the unpacked archive
preserves enough information to “Spread” (copy data and scripts to their
final locations) at any later time.

The wheel project provides a `bdist_wheel` command for setuptools
(requires distribute >= 0.6.28). Wheel files can be installed with a
patched `pip` from https://github.com/dholth/pip.

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

Usage
-----

The current version of wheel can be used to speed up repeated
installations by reducing the number of times you have to compile your
software. When you are creating a virtualenv for each revision of your
software, the savings can be dramatic. This example packages pyramid
and all its dependencies as wheels, and then installs pyramid from the
built packages::

        # Install pip, wheel
        pip install git+https://github.com/dholth/pip#egg=pip wheel

        # Build a directory of wheels
        mkdir /tmp/wheel-cache
        pip install --wheel-cache=/tmp/wheel-cache --no-install pyramid
        
        # Install from cached wheels
        pip install --use-wheel --no-index --find-links=file:///tmp/wheel-cache pyramid

For lxml, an up to 3-minute "search for the newest version and compile"
can become a less-than-1 second "unpack from wheel".

To build an individual wheel, run ``python setup.py bdist_wheel``.  Note that
``bdist_wheel`` only works with distribute (``import setuptools``); plain
``distutils`` does not support pluggable commands like ``bdist_wheel``.  On
the other hand ``pip`` always runs ``setup.py`` with setuptools enabled.

Wheel also includes its own installer that has the advantage of working even when
distribute has not been installed, and that can be invoked directly from wheel's
own wheel.



Automatically sign wheel files
------------------------------

`python setup.py bdist_wheel` will automatically sign wheel files if
the environment variable `WHEEL_TOOL` is set to the path of the `wheel`
command line tool::

	# Install the wheel tool and its dependencies
	$ pip install wheel[tool]
	# Generate a signing key (only once)
	$ wheel keygen
	    
	$ export WHEEL_TOOL=/path/to/wheel	
	$ python setup.py bdist_wheel
	
Signing is done in a subprocess because it is not convenient for 
the build environment to contain bindings to the keyring and 
cryptography libraries.

A future version of `wheel sign` will be able to choose different signing
keys depending on the package name, in case a user wishes to reserve a more
widely trusted key for packages they intend to distribute.

Format
------

The wheel format is being documented as PEP 427 "The Wheel Binary Package
Format 1.0" (http://www.python.org/dev/peps/pep-0427/).

Slogans
-------

Wheel

* Because ‘newegg’ was taken.
* Python packaging - reinvented.
* A container for cheese.

.. toctree::
   :maxdepth: 2
   
   story

