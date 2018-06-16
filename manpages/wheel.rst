:orphan:

wheel manual page
=================

Synopsis
--------

**wheel** [*command*] [*options*]


Description
-----------

:program:`wheel` installs and operates on `PEP 427`_ format binary wheels.


Commands
--------
  ``keygen``
    Generate signing key

  ``sign``
    Sign wheel

  ``unsign``
    Remove ``RECORD.jws`` from a wheel by truncating the zip file.
    ``RECORD.jws`` must be at the end of the archive.  The zip file must be an
    ordinary archive, with the compressed files and the directory in the same
    order, and without any non-zip content after the truncation point.

  ``verify``
    Verify a wheel.  The signature will be verified for internal consistency
    *only* and printed.  Wheel's own ``unpack`` and ``install`` commands
    verify the manifest against the signature and file contents.

  ``unpack``
    Unpack wheel

  ``install``
    Install wheels

  ``install-scripts``
    Install console scripts

  ``convert``
    Convert egg or wininst to wheel

  ``version``
    Print version and exit

  ``help``
    Show this help

Try ``wheel <command> --help`` for more information.


Options
-------
  -h, --help            show this help message and exit


.. _`PEP 427`: https://www.python.org/dev/peps/pep-0427/
