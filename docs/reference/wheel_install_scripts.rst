wheel install-scripts
=====================

Usage
-----

::

    wheel install-scripts <distribution>


Description
-----------

Install wrappers for the ``console_scripts`` entry points for given
distribution.

This (re)generates any wrappers (``.exe`` on Windows) for any
``console_scripts`` entry points and installs them in the current scripts
directory.

Options
-------

This command has no options.


Examples
--------

::

    $ wheel install-scripts someproject
