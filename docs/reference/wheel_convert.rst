wheel convert
=============

Usage
-----

::

    wheel convert [options] <egg_file_or_directory> [egg_file_or_directory...]


Description
-----------

Convert one or more eggs (``.egg``; made with ``bdist_egg``) or Windows
installers (``.exe``; made with ``bdist_wininst``) into wheels.

Egg names must match the standard format:

* ``<project>-<version>-pyX.Y`` for pure Python wheels
* ``<project>-<version>-pyX.Y-<arch>`` for binary wheels


Options
-------

.. option:: -d, --dest-dir <dir>

    Directory to store the generated wheels in (defaults to current directory).


Examples
--------

* Convert a single egg file::

    $ wheel convert foobar-1.2.3-py2.7.egg
    $ ls *.whl
    foobar-1.2.3-py27-none.whl

* If the egg file name is invalid::

    $ wheel convert pycharm-debug.egg
    "pycharm-debug.egg" is not a valid egg name (must match at least name-version-pyX.Y.egg)
    $ echo $?
    1
