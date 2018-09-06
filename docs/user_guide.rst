User Guide
==========

Building Wheels
---------------

Building wheels from a setuptools_ based project is simple::

    python setup.py bdist_wheel

This will build any C extensions in the project and then package those and the
pure Python code into a ``.whl`` file in the ``dist`` directory.

If your project contains no C extensions and is expected to work on both
Python 2 and 3, you will want to tell wheel to produce universal wheels by
adding this to your ``setup.cfg`` file:

.. code-block:: ini

    [bdist_wheel]
    universal = 1

.. _setuptools: https://pypi.org/project/setuptools/

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
    As of wheel v1.0, this option has been deprecated in favor of the more
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

.. note:: The ``wheel install`` command is merely a Proof-Of-Concept
    implementation and lacks many features provided by pip_. It is meant only
    as an example for implementors of packaging tools. End users should use
    ``pip install`` instead.

To install a wheel file in ``site-packages``::

    $ wheel install someproject-1.5.0-py2-py3-none.whl

This will unpack the archive in your current site packages directory and
install any console scripts contained in the wheel.

You can accomplish the same in two separate steps (with ``<site-packages-dir>``
being the path to your ``site-packages`` directory::

    $ wheel unpack -d <site-packages-dir> someproject-X.Y.Z-py2-py3-none.whl
    $ wheel install-scripts someproject

.. _pip: https://pypi.org/project/pip/
