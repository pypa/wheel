wheel keygen
============

Usage
-----

::

    wheel keygen


Description
-----------

Generates an ED25519 keypair for the purpose of signing wheels.

Repeated invocations of this command will each add a new key to the keyring.
The latest key will always be used for signing wheels.

Options
-------

This command has no options.


Examples
--------

::

    $ wheel keygen
    Created Ed25519 keypair with vk=ArGKRsTbmnMcO5aW2Of4xkictMrmUyxutJStwzlZcDk
    in <PlaintextKeyring with no encyption v.1.0 at /home/alex/.local/share/python_keyring/keyring_pass.cfg>
    Trusting ArGKRsTbmnMcO5aW2Of4xkictMrmUyxutJStwzlZcDk to sign and verify all packages.

.. note:: The above key is not actually used to sign any wheels, so do not
    trust it!
