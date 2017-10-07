User Guide
==========

.. toctree::

Building Wheels
---------------

    python setup.py bdist_wheel

If your project contains no binary wheels and is expected to work on both
Python 2 and 3, you will want to tell wheel to produce universal wheels by
adding this to your ``setup.cfg`` file:

.. code-block:: ini

    [bdist_wheel]
    universal = 1

Signing and Verifying Wheels
----------------------------

.. note:: For wheel signing to work, the appropriate dependencies must be
    installed. See the :doc:`installing` section for more information.

Wheels can be signed to help ensure that their contents have not been tampered
with after they were created. To sign a wheel, you must first have an ED25519
keypair which can be generated as such::

    $ wheel keygen

This will generate and store a key pair on your hard drive. You do not normally
need to do this more than once.

To sign an existing wheel file with this key::

    $ wheel sign someproject-X.Y.Z-py2-py3-none.whl

Verifying a wheel file can be done with following command::

    $ wheel verify someproject-X.Y.Z-py2-py3-none.whl

This will verify the internal consistency of the wheel file against the
contained signatures. It will also print out the key algorithm, verification
key and the hash of the wheel file for verification against external sources.

.. warning:: Wheel can only verify that the archive contents match the signing
    key. It **cannot** verify that the wheel was created by a trusted entity.
    For that, you must manually compare the verification key (``vk`` in the
    output) against the expected key(s).

You can also use wheel to remove the signature from a wheel file::

    $ wheel unsign someproject-X.Y.Z-py2-py3-none.whl

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

    $ wheel install someproject-X.Y.Z-py2-py3-none.whl

This will unpack the archive in your current site packages directory and
install any console scripts contained in the wheel.

You can accomplish the same in two separate steps (with ``<site-packages-dir>``
being the path to your ``site-packages`` directory::

    $ wheel unpack -d <site-packages-dir> someproject-X.Y.Z-py2-py3-none.whl
    $ wheel install-scripts someproject

.. _pip: https://pip.pypa.io/en/stable/installing/
