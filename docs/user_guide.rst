User Guide
==========

Building Wheels
---------------

To build a wheel for your project::

    python -m pip install build
    python -m build --wheel

This will build any C extensions in the project and then package those and the
pure Python code into a ``.whl`` file in the ``dist`` directory.

If your project contains no C extensions and is expected to work on both
Python 2 and 3, you will want to tell wheel to produce universal wheels by
adding this to your ``setup.cfg`` file:

.. code-block:: ini

    [bdist_wheel]
    universal = 1


Including license files in the generated wheel file
---------------------------------------------------

Several open source licenses require the license text to be included in every
distributable artifact of the project. By default, ``wheel`` conveniently
includes files matching the following glob_ patterns in the ``.dist-info``
directory:

* ``AUTHORS*``
* ``COPYING*``
* ``LICEN[CS]E*``
* ``NOTICE*``

This can be overridden by setting the ``license_files`` option in the
``[metadata]`` section of the project's ``setup.cfg``. For example:

.. code-block:: cfg

   [metadata]
   license_files =
      license.txt
      3rdparty/*.txt

No matter the path, all the matching license files are written in the wheel in
the ``.dist-info`` directory based on their file name only.

By specifying an empty ``license_files`` option, you can disable this
functionality entirely.

.. note:: There used to be an option called ``license_file`` (singular).
    As of wheel v0.32, this option has been deprecated in favor of the more
    versatile ``license_files`` option.

.. _glob: https://docs.python.org/library/glob.html

Converting Eggs to Wheels
-------------------------

The wheel tool is capable of converting eggs to the wheel format.
It works on both ``.egg`` files and ``.egg`` directories, and you can convert
multiple eggs with a single command::

    wheel convert blah-1.2.3-py2.7.egg foo-2.0b1-py3.5.egg

The command supports wildcard expansion as well (via :func:`~glob.iglob`) to
accommodate shells that do not do such expansion natively::

    wheel convert *.egg

By default, the resulting wheels are written to the current working directory.
This can be changed with the ``--dest-dir`` option::

    wheel convert --dest-dir /tmp blah-1.2.3-py2.7.egg

Installing Wheels
-----------------

To install a wheel file, use pip_::

    $ pip install someproject-1.5.0-py2-py3-none.whl

.. _pip: https://pypi.org/project/pip/
