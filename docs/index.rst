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
software the savings can be dramatic. This example packages pyramid
and all its dependencies as wheels, and then installs pyramid from the
built packages::

        # Make sure you have the latest pip that supports wheel
        pip install --upgrade pip

        # Install wheel
        pip install wheel

        # Build a directory of wheels for pyramid and all its dependencies
        pip wheel --wheel-dir=/tmp/wheelhouse pyramid

        # Install from cached wheels
        pip install --use-wheel --no-index --find-links=/tmp/wheelhouse pyramid

        # Install from cached wheels remotely
        pip install --use-wheel --no-index --find-links=https://wheelhouse.example.com/ pyramid


For lxml, an up to 3-minute "search for the newest version and compile"
can become a less-than-1 second "unpack from wheel".

As a side effect the wheel directory, "/tmp/wheelhouse" in the example,
contains installable copies of the exact versions of your application's
dependencies.  By installing from those cached wheels
you can recreate that environment quickly and with no surprises.

To build an individual wheel, run ``python setup.py bdist_wheel``.  Note that
``bdist_wheel`` only works with distribute (``import setuptools``); plain
``distutils`` does not support pluggable commands like ``bdist_wheel``.  On
the other hand ``pip`` always runs ``setup.py`` with setuptools enabled.

Wheel also includes its own installer that can only install wheels (not
sdists) from a local file or folder, but has the advantage of working
even when distribute or pip has not been installed.

Wheel's builtin utility can be invoked directly from wheel's own wheel::

    $ python wheel-0.21.0-py2.py3-none-any.whl/wheel -h
    usage: wheel [-h]

                 {keygen,sign,unsign,verify,unpack,install,install-scripts,convert,help}
                 ...

    positional arguments:
      {keygen,sign,unsign,verify,unpack,install,install-scripts,convert,help}
                            commands
        keygen              Generate signing key
        sign                Sign wheel
        unsign              Remove RECORD.jws from a wheel by truncating the zip
                            file. RECORD.jws must be at the end of the archive.
                            The zip file must be an ordinary archive, with the
                            compressed files and the directory in the same order,
                            and without any non-zip content after the truncation
                            point.
        verify              Verify a wheel. The signature will be verified for
                            internal consistency ONLY and printed. Wheel's own
                            unpack/install commands verify the manifest against
                            the signature and file contents.
        unpack              Unpack wheel
        install             Install wheels
        install-scripts     Install console_scripts
        convert             Convert egg or wininst to wheel
        help                Show this help

    optional arguments:
      -h, --help            show this help message and exit

Setuptools scripts handling
---------------------------

Setuptools' popular `console_scripts` and `gui_scripts` entry points can
be used to generate platform-specific scripts wrappers.  Most usefully
these wrappers include `.exe` launchers if they are generated on a
Windows machine.

By default `bdist_wheel` puts pre-generated versions of these wrappers
into the `*.data/scripts/` directory of the archive.  This means a
Windows user may have trouble running scripts from a wheel generated
on Unix and vice-versa.  As of version 0.21.0 `python setup.py
bdist_wheel --skip-scripts` is available to create wheels that do not
contain the setuptools script wrappers. The wheel tool `python -m wheel
install-scripts packagename` calls setuptools to write the appropriate
scripts wrappers after an install.

Defining the Python version
---------------------------

The `bdist_wheel` command automatically determines the correct tags to use for
the generated wheel. These are based on the Python interpreter used to
generate the wheel and whether the project contains C extension code or not.
While this is usually correct for C code, it can be too conservative for pure
Python code.  The bdist_wheel command therefore supports two flags that can be
used to specify the Python version tag to use more precisely::

    --universal        Specifies that a pure-python wheel is "universal"
                       (i.e., it works on any version of Python).  This
                       equates to the tag "py2.py3".
    --python-tag XXX   Specifies the precise python version tag to use for
                       a pure-python wheel.

Neither of these two flags have any effect when used on a project that includes
C extension code.

A reasonable use of the `--python-tag` argument would be for a project that
uses Python syntax only introduced in a particular Python version.  There are
no current examples of this, but if wheels had been available when Python 2.5
was released (the first version containing the `with` statement), wheels for a
project that used the `with` statement would typically use `--python-tag py25`.

Typically, projects would not specify Python tags on the command line, but
would use `setup.cfg` to set them as a project default::

    [bdist_wheel]
    universal=1

or::

    [bdist_wheel]
    python-tag = py32


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

The wheel format is documented as PEP 427 "The Wheel Binary Package
Format..." (http://www.python.org/dev/peps/pep-0427/).

Slogans
-------

Wheel

* Because ‘newegg’ was taken.
* Python packaging - reinvented.
* A container for cheese.
* It makes it easier to roll out software.

.. toctree::
   :maxdepth: 2

   story
   api

