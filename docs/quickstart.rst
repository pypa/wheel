Quickstart
==========

To build a wheel for your setuptools based project::

    python setup.py bdist_wheel

The wheel will go to ``dist/yourproject-<tags>.whl``.

To generate a key for signing wheels (you just need to do this **once**)::

    wheel keygen

To sign a wheel file::

    wheel sign yourwheelfile.whl

To verify the signature of a signed wheel file::

    wheel verify yourwheelfile.whl

To convert an ``.egg`` file to a wheel::

    wheel convert youreggfile.egg
