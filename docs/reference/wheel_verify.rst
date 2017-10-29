wheel verify
============

Usage
-----

::

    wheel verify <wheel_file>


Description
-----------

Verify that the wheel's signature is internally consistent.

This does not verify the files in the archive contents. For that, you must use
the ``wheel unpack`` or ``wheel install`` commands.


Options
-------

This command has no options.


Examples
--------

* Verify a wheel::

    $ wheel verify someproject-X.Y.Z-py2-py3-none.whl

* If the wheel is not signed::

    $ wheel verify someproject-X.Y.Z-py2-py3-none.whl
    The wheel is not signed (RECORD.jws not found at end of the archive).
    $ echo $?
    1

