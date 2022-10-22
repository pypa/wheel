Quickstart
==========

To build a wheel for your project::

    python -m pip install build
    python -m build --wheel

The wheel will go to ``dist/yourproject-<tags>.whl``.

If you want to make universal (Python 2/3 compatible, pure Python) wheels, add the following
section to your ``setup.cfg``::

    [bdist_wheel]
    universal = 1

To convert an ``.egg`` or file to a wheel::

    wheel convert youreggfile.egg

Similarly, to convert a Windows installer (made using ``python setup.py bdist_wininst``) to a
wheel::

    wheel convert yourinstaller.exe
