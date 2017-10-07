Installation
============

You can use pip_ to install wheel::

    pip install wheel

If you do not have pip_ installed, see its documentation for
`installation instructions`_.

If you intend to use wheel for sign wheels, you will need to include the
``signatures`` extra when using pip_ to install::

    pip install wheel[signatures]

If you prefer using your system package manager to install Python packages, you
can typically find the wheel package under one of the following package names:

* python-wheel
* python2-wheel
* python3-wheel

For the wheel signing dependencies, you will have to match the dependencies in
wheel's extras_require_ against your system packages to find the right ones.

.. _pip: https://pip.pypa.io/en/stable/
.. _installation instructions: https://pip.pypa.io/en/stable/installing/
.. _extras_require: https://github.com/pypa/wheel/blob/master/setup.py

Python and OS Compatibility
---------------------------

wheel should work on any Python implementation and operating system and is
compatible with Python version 2.7 and upwards of 3.4.
