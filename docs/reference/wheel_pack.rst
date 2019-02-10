wheel pack
==========

Usage
-----

::

    wheel pack <wheel_directory>


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

.. option:: --build-number <tag>

    Override the build tag in the new wheel file name

Examples
--------

* Unpack a wheel, add a dummy module and then repack it (with a new build number)::

    $ wheel unpack someproject-1.5.0-py2-py3-none.whl
    Unpacking to: ./someproject-1.5.0
    $ touch someproject-1.5.0/somepackage/module.py
    $ wheel pack --build-number 2 someproject-1.5.0
    Repacking wheel as ./someproject-1.5.0-2-py2-py3-none.whl...OK
