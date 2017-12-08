Quickstart
==========

Make sure you have the latest pip that supports wheel::

  pip install --upgrade pip

Install wheel::

  pip install wheel

Build a wheel::

  python setup.py bdist_wheel

Build a directory of wheels for pyramid and all its dependencies::

  pip wheel --wheel-dir=/tmp/wheelhouse pyramid

Install from cached wheels::

  pip install --use-wheel --no-index --find-links=/tmp/wheelhouse pyramid

Install from cached wheels remotely::

  pip install --use-wheel --no-index --find-links=https://wheelhouse.example.com/ pyramid
