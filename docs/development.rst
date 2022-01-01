Development
===========

Pull Requests
-------------

- Submit Pull Requests against the ``main`` branch.
- Provide a good description of what you're doing and why.
- Provide tests that cover your changes and try to run the tests locally first.

**Example**. Assuming you set up GitHub account, forked wheel repository from
https://github.com/pypa/wheel to your own page via web interface, and your
fork is located at https://github.com/yourname/wheel

::

  $ git clone git@github.com:pypa/wheel.git
  $ cd wheel
  # ...
  $ git diff
  $ git add <modified> ...
  $ git status
  $ git commit

You may reference relevant issues in commit messages (like #1259) to
make GitHub link issues and commits together, and with phrase like
"fixes #1259" you can even close relevant issues automatically. Now
push the changes to your fork::

  $ git push git@github.com:yourname/wheel.git

Open Pull Requests page at https://github.com/yourname/wheel/pulls and
click "New pull request". That's it.

Automated Testing
-----------------

All pull requests and merges to ``main`` branch are tested in `GitHub Actions`_
based on the workflows in the ``.github`` directory.

The only way to trigger the test suite to run again for a pull request is to
submit another change to the pull branch.

.. _GitHub Actions: https://github.com/actions

Running Tests Locally
---------------------

Python requirements: tox_ or pytest_

To run the tests via tox against all matching interpreters::

  $ tox

To run the tests via tox against a specific environment::

  $ tox -e py35

Alternatively, you can run the tests via pytest using your default interpreter::

  $ pip install -e .[test]  # Installs the test dependencies
  $ pytest                  # Runs the tests with the current interpreter

The above pip install command will replace the current interpreter's installed
wheel package with the development package being tested. If you use this
workflow, it is recommended to run it under a virtualenv_.

.. _tox: https://pypi.org/project/tox/
.. _pytest: https://pypi.org/project/pytest/
.. _virtualenv: https://pypi.org/project/virtualenv/

Getting Involved
----------------

The wheel project welcomes help in the following ways:

- Making Pull Requests for code, tests, or docs.
- Commenting on open issues and pull requests.
- Helping to answer questions on the `mailing list`_.

.. _`mailing list`: https://mail.python.org/mailman/listinfo/distutils-sig

Release Process
---------------

To make a new release:

#. Edit ``docs/news.rst`` and replace ``**UNRELEASED**`` with a release version
   and date, like ``**X.Y.Z (20XX-YY-ZZ)**``.
#. Replace the ``__version__`` attribute in ``src/wheel/__init__.py`` with the
   same version number as above (without the date of course).
#. Create a new git tag matching the version exactly
#. Push the new tag to GitHub

Pushing a new tag to GitHub will trigger the publish workflow which package the
project and publish the resulting artifacts to PyPI.
