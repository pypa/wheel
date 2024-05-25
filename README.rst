wheel
=====

This is a command line tool for manipulating Python wheel files, as defined in
`PEP 427`_. It contains the following functionality:

* Convert ``.egg`` archives into ``.whl``
* Unpack wheel archives
* Repack wheel archives
* Add or remove tags in existing wheel archives

Historical note
---------------

This library used to be the reference implementation of the Python wheel packaging
standard, and a setuptools_ extension containing the ``bdist_wheel`` command. The wheel
file processing functionality has since been moved to the packaging_ library, and the
``bdist_wheel`` command has been merged into setuptools itself, leaving this project to
only contain the command line interface.

.. _PEP 427: https://www.python.org/dev/peps/pep-0427/
.. _packaging: https://pypi.org/project/packaging/
.. _setuptools: https://pypi.org/project/setuptools/

Documentation
-------------

The documentation_ can be found on Read The Docs.

.. _documentation: https://wheel.readthedocs.io/

Code of Conduct
---------------

Everyone interacting in the wheel project's codebases, issue trackers, chat
rooms, and mailing lists is expected to follow the `PSF Code of Conduct`_.

.. _PSF Code of Conduct: https://github.com/pypa/.github/blob/main/CODE_OF_CONDUCT.md
