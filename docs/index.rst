.. wheel documentation master file, created by
   sphinx-quickstart on Thu Jul 12 00:14:09 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. include:: ../README.txt

Usage
-----

The current version of wheel can be used to speed up repeated
installations by reducing the number of times you have to compile your
software. When you are creating a virtualenv for each revision of your
software, the savings can be dramatic. This example packages pyramid
and all its dependencies as wheels, and then installs pyramid from the
built packages::

        # Install pip (the wheel_build branch)
        pip install -e git+https://github.com/qwcode/pip@wheel_build#egg=pip
        # Install wheel
        pip install wheel

        # Build a directory of wheels for pyramid and all its dependencies
        pip install --wheel-dir=/tmp/wheelhouse pyramid
        
        # Install from cached wheels
        pip install --use-wheel --no-index --find-links=/tmp/wheelhouse pyramid

For lxml, an up to 3-minute "search for the newest version and compile"
can become a less-than-1 second "unpack from wheel".

To build an individual wheel, run ``python setup.py bdist_wheel``.  Note that
``bdist_wheel`` only works with distribute (``import setuptools``); plain
``distutils`` does not support pluggable commands like ``bdist_wheel``.  On
the other hand ``pip`` always runs ``setup.py`` with setuptools enabled.

Wheel also includes its own installer that can only install wheels (not
sdists) from a local file or folder, but has the advantage of working
even when distribute or pip has not been installed.

Wheel's builtin utility can be invoked directly from wheel's own wheel::

    $ python wheel-0.13.0-py2.py3-none-any.whl/wheel -h
    usage: wheel [-h] {keygen,sign,verify,unpack,install,convert,help} ...

    positional arguments:
      {keygen,sign,verify,unpack,install,convert,help}
                            commands
        keygen              Generate signing key
        sign                Sign wheel
        verify              Verify signed wheel
        unpack              Unpack wheel
        install             Install wheels
        convert             Convert egg or wininst to wheel
        help                Show this help

    optional arguments:
      -h, --help            show this help message and exit


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

Signing is done in a subprocess because it is not convenient for the
build environment to contain bindings to the keyring and cryptography
libraries. The keyring library may not be able to find your keys (choosing
a different key storage back end based on available dependencies) unless
you run it from the same environment used for keygen.

A future version of `wheel sign` will be able to choose different signing
keys depending on the package name, in case a user wishes to reserve a
more widely trusted key for packages they intend to distribute.

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

