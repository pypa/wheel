.. wheel documentation master file, created by
   sphinx-quickstart on Thu Jul 12 00:14:09 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. include:: ../README.rst

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
        pip install --only-binary=:all: --no-index --find-links=/tmp/wheelhouse pyramid

        # Install from cached wheels remotely
        pip install --only-binary=:all: --no-index --find-links=https://wheelhouse.example.com/ pyramid


For lxml, an up to 3-minute "search for the newest version and compile"
can become a less-than-1 second "unpack from wheel".

As a side effect the wheel directory, "/tmp/wheelhouse" in the example,
contains installable copies of the exact versions of your application's
dependencies.  By installing from those cached wheels
you can recreate that environment quickly and with no surprises.

To build an individual wheel, run ``python setup.py bdist_wheel``.  Note that
``bdist_wheel`` only works with setuptools (``import setuptools``); plain
``distutils`` does not support pluggable commands like ``bdist_wheel``.  On
the other hand ``pip`` always runs ``setup.py`` with setuptools enabled.

Wheel also includes its own installer that can only install wheels (not
sdists) from a local file or folder, but has the advantage of working
even when setuptools or pip has not been installed.

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

As of 0.23.0, `bdist_wheel` no longer places pre-generated versions of these
wrappers into the `*.data/scripts/` directory of the archive (non-setuptools
scripts are still present, of course).

If the scripts are needed, use a real installer like `pip`.  The wheel tool
`python -m wheel install-scripts package [package ...]` can also be used at
any time to call setuptools to write the appropriate scripts wrappers.

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
    --py-limited-api {cp32|cp33|cp34|...}
                       Specifies Python Py_LIMITED_API compatibility with
                       the version of CPython passed and later versions.
                       The wheel will be tagged cpNN.abi3.{arch} on CPython 3.
                       This flag does not affect Python 2 builds or alternate
                       Python implementations.

                       To conform to the limited API, all your C
                       extensions must use only functions from the limited
                       API, pass Extension(py_limited_api=True) and e.g.
                       #define Py_LIMITED_API=0x03020000 depending on
                       the exact minimun Python you wish to support.

The --universal and --python-tag flags have no effect when used on a
project that includes C extension code.

The default for a pure Python project (if no explicit flags are given) is "pyN"
where N is the major version of the Python interpreter used to build the wheel.
This is generally the correct choice, as projects would not typically ship
different wheels for different minor versions of Python.

A reasonable use of the `--python-tag` argument would be for a project that
uses Python syntax only introduced in a particular Python version.  There are
no current examples of this, but if wheels had been available when Python 2.5
was released (the first version containing the `with` statement), wheels for a
project that used the `with` statement would typically use `--python-tag py25`.
However, unless a separate version of the wheel was shipped which avoided the
use of the new syntax, there is little benefit in explicitly marking the tag in
this manner.

Typically, projects would not specify Python tags on the command line, but
would use `setup.cfg` to set them as a project default::

    [bdist_wheel]
    universal=1

or::

    [bdist_wheel]
    python-tag = py32

Defining conditional dependencies
---------------------------------

In wheel, the only way to have conditional dependencies (that might only be
needed on certain platforms) is to use environment markers as defined by
:pep:`508`.

As of wheel 0.24.0, the recommended way to do this is in the setuptools
``extras_require`` parameter. A ``:`` separates the extra name from the marker.
Wheel's own setup.py has an example::

   extras_require={
       'signatures': ['keyring'],
       'signatures:sys_platform!="win32"': ['pyxdg'],
       'faster-signatures': ['ed25519ll']
   },

Leaving out the name of the extra (like with "argparse" here) means that only
the conditions after ``:`` determine whether the dependencies will be installed
or not.

As of setuptools 36.2.1, you can pass extras as part of ``install_requires``.
The above requirements could thus be written like this::

   install_requires=[
       'keyring; extra=="signatures"',
       'pyxdg; extra=="signatures" and sys_platform!="win32"',
       'ed25519ll; extra=="faster-signatures"'
   ]

Alternatively (as of setuptools 36.2.7), you can specify your requirements in
the ``[options]`` section of your setup.cfg:

.. code-block:: cfg

   [options]
   install_requires =
       argparse; python_version=="2.6"
       keyring; extra=="signatures"
       pyxdg; extra=="signatures" and sys_platform!="win32"
       ed25519ll; extra=="faster-signatures"

.. warning:: Specifying extras via ``install_requires`` does not yet work with
   pip (v9.0.1 as of this writing).

Including the license in the generated wheel file
-------------------------------------------------

Several open source licenses require the license text to be included in every
distributable artifact of the project. Currently, the only way to to do this
with "wheel" is to specify the ``license_file`` key in the ``[metadata]``
section of the project's ``setup.cfg``:

.. code-block:: cfg

   [metadata]
   license_file = LICENSE.txt

The file path should be relative to the project root. The file will be
packaged as ``LICENSE.txt`` (regardless of the original name) in the
``.dist-info`` directory in the wheel.

There is currently no way to include multiple license related files, but
this is going to change in the near future. You can track the progress
by subscribing to `issue 138`_ on Github.

.. _issue 138: https://github.com/pypa/wheel/issues/138

Automatically sign wheel files
------------------------------

Wheel contains an experimental digital signatures scheme based on Ed25519
signatures; these signatures are unrelated to pgp/gpg signatures and do not
include a trust model.

`python setup.py bdist_wheel` will automatically sign wheel files if
the environment variable `WHEEL_TOOL` is set to the path of the `wheel`
command line tool.::

    # Install wheel with dependencies for generating signatures
    $ pip install wheel[signatures]
    # Generate a signing key (only once)
    $ wheel keygen

    $ export WHEEL_TOOL=/path/to/wheel
    $ python setup.py bdist_wheel

Signing is done in a subprocess because it is not convenient for the
build environment to contain bindings to the keyring and cryptography
libraries. The keyring library may not be able to find your keys (choosing
a different key storage back end based on available dependencies) unless
you run it from the same environment used for keygen.

.. warning:: This functionality has been scheduled for removal before the
    v1.0.0 release.

.. note:: You can also include the ``faster-signatures`` extra when
          installing "wheel" to improve the performance of wheel signing.

Format
------

The wheel format is documented as PEP 427 "The Wheel Binary Package
Format..." (https://www.python.org/dev/peps/pep-0427/).

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
