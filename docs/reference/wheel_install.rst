wheel install
=============

Usage
-----

::

    wheel install <wheel_file>


Description
-----------

Install the given wheel file to ``site-packages``.

This unpacks the wheel file to the site packages directory and installs
wrappers for any console scripts defined in the wheel metadata.

It also checks that the hashes and file sizes match with those in ``RECORD``
and exits with an error if it encounters a mismatch.


Options
-------

.. option:: --force

    Install the wheel even if its tags indicate it is incompatible with the
    current CPU architecture, Python version or Python implementation.

.. options:: -d, --wheel-dir <wheel_dir>

    Specify a directory containing wheels. This will be used for dependency
    lookup.

.. option:: -r, --requirements-file <requirements_file>

    Specify a file containing requirements to install. The wheels listed here
    will be installed in addition to the wheel given as the argument.

.. option:: -l, --list

    List wheels which would be installed, but don't actually install anything.

Examples
--------

* Unpack a wheel::

    $ wheel install someproject-1.5.0-py2-py3-none.whl
    Unpacking to: ./someproject-1.5.0

* If a file's hash does not match::

    $ wheel install someproject-1.5.0-py2-py3-none.whl
    Unpacking to: ./someproject-1.5.0
    Traceback (most recent call last):
    ...
    wheel.install.BadWheelFile: Bad hash for file 'mypackage/module.py'
    $ echo $?
    1

