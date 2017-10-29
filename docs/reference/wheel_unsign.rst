wheel unsign
============

Usage
-----

::

    wheel unsign <wheel_file>


Description
-----------

Remove the digital signature from the given wheel file.

This removes the ``RECORD.jws`` file from the end of the archive.


Options
-------

This command has no options.


Examples
--------

* Unsign a wheel::

    $ wheel unsign someproject-X.Y.Z-py2-py3-none.whl

* If the wheel isn't signed::

    $ wheel unsign someproject-X.Y.Z-py2-py3-none.whl
    The wheel is not signed (RECORD.jws not found at end of the archive).
    $ echo $?
    1

