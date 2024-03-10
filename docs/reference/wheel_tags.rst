wheel tags
==========

Usage
-----

::

    wheel tags [-h] [--remove] [--python-tag TAG] [--abi-tag TAG] [--platform-tag TAG] [--build NUMBER] WHEEL [...]

Description
-----------

Make a new wheel with given tags from an existing wheel. Any tags left
unspecified will remain the same. Multiple tags are separated by a "." Starting
with a "+" will append to the existing tags.  Starting with a "-" will remove a
tag. Be sure to use the equals syntax on the shell so that it does not get
parsed as an extra option, such as ``--python-tag=-py2``. The original file
will remain unless ``--remove`` is given. The output filename(s) will be
displayed on stdout for further processing.


Options
-------

.. option:: --remove

    Remove the original wheel, keeping only the retagged wheel.

.. option:: --python-tag=TAG

    Override the python tag (prepend with "+" to append, "-" to remove).
    Multiple tags can be separated with a dot.

.. option:: --abi-tag=TAG

    Override the abi tag (prepend with "+" to append, "-" to remove).
    Multiple tags can be separated with a dot.

.. option:: --platform-tag=TAG

    Override the platform tag (prepend with "+" to append, "-" to remove).
    Multiple tags can be separated with a dot.

.. option:: --build=NUMBER

    Specify a build number.

Examples
--------

* Replace a wheel's Python specific tags with generic tags (if no Python extensions are present, for example)::

    $ wheel tags --python-tag=py2.py3 --abi-tag=none cmake-3.20.2-cp39-cp39-win_amd64.whl
    cmake-3.20.2-py2.py3-none-win_amd64.whl

* Add compatibility tags for macOS universal wheels and older pips::

    $ wheel tags \
        --platform-tag=+macosx_10_9_x86_64.macosx_11_0_arm64 \
        ninja-1.11.1-py2.py3-none-macosx_10_9_universal2.whl
    ninja-1.11.1-py2.py3-none-macosx_10_9_universal2.macosx_10_9_x86_64.macosx_11_0_arm64.whl
