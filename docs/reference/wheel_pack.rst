wheel repack
============

Usage
-----

::

    wheel repack <wheel_directory>


Description
-----------

Repack a previously unpacked wheel file.

This command can be used to repack a wheel file after its contents have been modified.
This is the equivalent of ``zip -r <wheel_file> <wheel_directory>`` except that it regenerates the
``RECORD`` file which contains hashes of all included files.


Options
-------

.. option:: -d, --dest-dir <dir>

    Directory to put the new wheel file into.


Examples
--------

* Unpack a wheel, add a dummy module and then repack it::

    $ wheel unpack someproject-1.5.0-py2-py3-none.whl
    Unpacking to: ./someproject-1.5.0
    $ touch someproject-1.5.0/somepackage/module.py
    $ wheel repack someproject-1.5.0
    Repacking wheel as ./someproject-1.5.0-py2-py3-none.whl...OK
