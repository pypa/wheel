wheel unpack
============

Usage
-----

::

    wheel unpack <wheel_file>


Description
-----------

Unpack the given wheel file.

This is the equivalent of ``unzip <wheel_file>``, except that it also checks
that the hashes and file sizes match with those in ``RECORD`` and exits with an
error if it encounters a mismatch.


Options
-------

.. option:: -d, --dest <dir>

    Directory to unpack the wheel into.


Examples
--------

* Unpack a wheel::

    $ wheel unpack someproject-1.5.0-py2-py3-none.whl
    Unpacking to: ./someproject-1.5.0

* If a file's hash does not match::

    $ wheel unpack someproject-1.5.0-py2-py3-none.whl
    Unpacking to: ./someproject-1.5.0
    Traceback (most recent call last):
    ...
    wheel.install.BadWheelFile: Bad hash for file 'mypackage/module.py'
    $ echo $?
    1
