wheel
=====

A built-package format for Python.

.. image:: https://img.shields.io/pypi/v/wheel.svg
   :target: https://pypi.python.org/pypi/wheel

.. image:: https://img.shields.io/travis/pypa/wheel/master.svg
   :target: http://travis-ci.org/pypa/wheel

.. Appveyor is not set up for Wheel yet!
   .. image:: https://img.shields.io/appveyor/ci/pypa/wheel.svg
      :target: https://ci.appveyor.com/project/pypa/wheel/history

.. image:: https://readthedocs.org/projects/wheel/badge/?version=latest
   :target: https://wheel.readthedocs.io/en/latest/

* `Installation`_
* `Documentation`_
* `GitHub Page`_
* `Issue Tracking`_
* User IRC: #pypa on Freenode.
* Dev IRC: #pypa-dev on Freenode.


A wheel is a ZIP-format archive with a specially formatted filename
and the .whl extension. It is designed to contain all the files for a
PEP 376 compatible install in a way that is very close to the on-disk
format. Many packages will be properly installed with only the "Unpack"
step (simply extracting the file onto sys.path), and the unpacked archive
preserves enough information to "Spread" (copy data and scripts to their
final locations) at any later time.

The wheel project provides a `bdist_wheel` command for setuptools
(requires setuptools >= 0.8.0). Wheel files can be installed with a
newer `pip` from https://github.com/pypa/pip or with wheel's own command
line utility.

Code of Conduct
---------------

Everyone interacting in the wheel project's codebases, issue trackers, chat
rooms, and mailing lists is expected to follow the `PyPA Code of Conduct`_.

.. _Installation: https://wheel.readthedocs.io/en/stable/installing.html
.. _Documentation: https://wheel.readthedocs.io/en/stable/
.. _GitHub Page: https://github.com/pypa/wheel
.. _Issue Tracking: https://github.com/pypa/wheel/issues
.. _PyPA Code of Conduct: https://www.pypa.io/en/latest/code-of-conduct/
