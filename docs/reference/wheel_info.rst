wheel info
==========

Usage
-----

::

    wheel info [OPTIONS] <wheel_file>


Description
-----------

Display information about a wheel file without unpacking it.

This command shows comprehensive metadata about a wheel file including:

* Package name, version, and build information
* Wheel format version and generator
* Supported Python versions, ABI, and platform tags
* Package metadata such as summary, author, and license
* Classifiers and dependencies
* File count and total size
* Optional detailed file listing


Options
-------

.. option:: -v, --verbose

    Show detailed file listing with individual file sizes.


Examples
--------

Display basic information about a wheel::

    $ wheel info example_package-1.0-py3-none-any.whl
    Name: example-package
    Version: 1.0
    Wheel-Version: 1.0
    Root-Is-Purelib: true
    Tags:
      py3-none-any
    Generator: bdist_wheel (0.40.0)
    Summary: An example package
    Author: John Doe
    License: MIT
    Files: 12
    Size: 15,234 bytes

Display detailed information with file listing::

    $ wheel info --verbose example_package-1.0-py3-none-any.whl
    Name: example-package
    Version: 1.0
    ...
    
    File listing:
      example_package/__init__.py                                      45 bytes
      example_package/module.py                                     1,234 bytes
      example_package-1.0.dist-info/METADATA                         678 bytes
      example_package-1.0.dist-info/WHEEL                            123 bytes
      example_package-1.0.dist-info/RECORD                           456 bytes
