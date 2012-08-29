.. wheel documentation master file, created by
   sphinx-quickstart on Thu Jul 12 00:14:09 2012.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Wheel
=====

A built-package format for Python.

A wheel is a ZIP-format archive with a specially formatted filename and
the .whl extension. It is designed to contain all the files for a PEP 376
compatible install in a way that is very close to the on-disk format. Many
packages will be properly installed with only the “Unpack” step
(simply extracting the file onto sys.path), and the unpacked archive
preserves enough information to “Spread” (copy data and scripts to their
final locations) at any later time.

The wheel project provides a `bdist_wheel` command for setuptools
(requires distribute >= 0.6.28). Wheel files can be installed with a
patched `pip` from https://github.com/dholth/pip.

Why not egg?
------------

Python's egg format predates the packaging related standards we have today,
the most important being PEP 376 "Database of Installed Python Distributions"
which specifies the .dist-info directory (instead of .egg-info) and PEP 345 
"Metadata for Python Software Packages 1.2" which specifies how to express
dependencies (instead of requires.txt in .egg-info).

Wheel implements these things. It also provides a richer file naming
convention that communicates the Python implementation and ABI as well as
simply the language version used in a particular package.

Unlike .egg, wheel will be a fully-documented standard at the binary level
that is truly easy to install even if you do not want to use the reference
implementation.

Usage
-----

The current version of wheel can be used to speed up repeated
installations by reducing the number of times you have to compile your
software. When you are creating a virtualenv for each new version of your
software, the savings can be
dramatic. This script from the wheel source code builds a virtualenv
that can build and understand wheels, packages pyramid and all its
dependencies as wheels, and then installs pyramid from the built packages.

wheeldemo.sh::

        #!/bin/sh
        set -e

        # bdist_wheel demo

        # Create environment
        virtualenv --distribute /tmp/wheeldemo
        cd /tmp/wheeldemo

        # Install wheel and patched pip
        bin/pip install --upgrade --ignore-installed \
                git+https://github.com/dholth/pip.git#egg=pip
        bin/pip install hg+https://bitbucket.org/dholth/wheel#egg=wheel

        # Make sure it worked
        bin/python -c "import pkg_resources; pkg_resources.DistInfoDistribution"

        # Download an unpack a package and its dependencies into build/
        bin/pip install --build build --no-install --ignore-installed pyramid
        cd build

        # Make wheels for each package
        for i in `find . -maxdepth 1 -mindepth 1 -type d`; do
                (cd $i; ../../bin/python -c "import setuptools, sys; sys.argv = ['', 'bdist_wheel']; __file__ = 'setup.py'; exec(compile(open('setup.py').read(), 'setup.py', 'exec'))")
        done

        # Copy them into a repository
        mkdir -p ../wheelbase
        find . -name *.whl -exec mv {} ../wheelbase \;
        cd ..

        # Remove build dir or pip will look there first
        rm -rf build

        # Install from saved wheels
        bin/pip install --no-index --find-links=file://$PWD/wheelbase pyramid

File Contents
-------------

Wheel files contain a folder `{distribution}-{version}.dist-info/` with the PEP 376 metadata and an additional file `WHEEL` with metadata about the package itself.

The root of a .whl is either purelib or platlib.

If a .whl contains scripts, both purelib and platlib, or any other files that 
are not installed on sys.path, they are found in `{distribution}-{version}.data/{key}`.

Wheel files contain metadata about the wheel format itself in `{distribution}-{version}/WHEEL` ::

        Wheel-Version: 0.9
        Packager: bdist_wheel-0.1
        Root-Is-Purelib: true


File name convention
--------------------

The wheel filename is `{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl`

distribution 
	Distribution name, e.g. ‘django’, ‘pyramid’
version
	PEP 386-compliant version, e.g. 1.0
build tag
	Optional build number. Must start with a digit. A tie breaker if two wheels have the same version. (Sorts as None if unspecified).
implementation and language version tag
	‘pp27’
abi tag
	‘cp33dmu’, 'none'
platform tag
	'linux_x86_64', 'any'
	
For example, package-1.0-py27-none-any.whl is compatible with Python 2.7 (any Python 2.7 implementation) on any CPU architecture.

The last three components of the file are called "compatibility tags."  The
compatibility tags express the package's basic interpreter requirements, and
are detailed in PEP 485 [http://hg.python.org/peps/file/tip/pep-0425.txt]. 

Ranking wheels with the same version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Installers will sometimes have to choose the best wheel among several
for the same version of a distribution. First, rank the supported
implementation tags by preference, e.g. CPython might prefer cp33m,
py33, py32. Second, choose the multi-wheel with the smallest arity. If
all else fails, rebuild from source.

Automatically sign wheel files
------------------------------

`bdist_wheel` will automatically sign wheel files if the environment variable
`WHEEL_TOOL` is set to the path of the `wheel` command line tool::

	# Install the wheel tool and its dependencies
	$ pip install wheel[tool]
	# Generate a signing key (only once)
	$ wheel keygen
	    
	$ export WHEEL_TOOL=/path/to/wheel	
	$ python setup.py bdist_wheel
	
Signing is done in a subprocess because it is not convenient for 
the build environment to contain bindings to the keyring and 
cryptography libraries.

Signed wheel files
------------------

Wheel files include an extended RECORD that enables
digital signatures. PEP 376’s RECORD is altered to include
digestname=urlsafe_b64encode_nopad(digest) (base64 encoding with no
trailing = characters) as the second column instead of an md5sum. All
possible entries are hashed, including .pyc and other generated files,
but not RECORD. For example::

        file.py,sha256=AVTFPZpEKzuHr7OvQZmhaU3LvwKz06AJw8mT_pNh2yI,3144

The signature is one or more JSON Web Signature JSON Serialization
(JWS-JS) signatures stored in a file RECORD.jws in the
.dist-info directory adjacent to RECORD. The JSON Web Signature
payload is an object with one key “hash” with a value of a
hash of RECORD stored in the same format as entries in RECORD:
digestname=urlsafe_b64encode_nopad(digest), but need not use the same
hash function as RECORD. The only supported signing algorithm is ‘JWS
using Ed25519’ and the only currently supported hash algorithm is sha256.

To verify, first verify the signature, then hash RECORD with the hashing
algorithm used in the signed payload and check for equality with the
signed payload, and finally verify that all the files contained in RECORD
actually hash to the values listed in RECORD.

Remember that files can be included in the wheel file without being
included in the signed RECORD; an implementation could choose to unpack
only the verified files. Verification must also reject signatures that
use hashing algorithms outside a list of trusted algorithms.

Public-key signed wheels bundle the (short) public key in the signature. A
wheel installer should always verify the internal consistency of any
bundled signatures and the hashes in RECORD while unpacking, and may
check that signatures come from a trusted signer.

A signature-aware installer can be instructed to check for a particular
Ed25519 public key by using an extended "extras" syntax.::

        # request a normal optional feature "extra", and a particular
        # urlsafe-b64encode-nopad Ed25519 (ed25519 is in lowercase within
        # the []) public key:
        package[extra, ed25519=ouBJlTJJ4SJXoy8Bi1KRlewWLU6JW7HUXTgvU1YRuiA]

An application could distribute a `requires.txt` file with many such
lines for all its dependencies and their public keys.  By installing
from this file an application's users would know whether the applicaton's
dependencies came from the correct publishers.

Applications that wish to "fail open" for backwards compatibility with
non-signature-aware installers should specify that their package provides
the extra `ed25519=(key)` with no associated dependencies.

Key distribution is outside the scope of this spec. Public wheel signing
keys could be signed with the packager’s GPG key, or stored at an
https://-protected URL.

The `wheel` command line tool can create signed wheel files with
`wheel sign wheelfilename.whl`. It generates a new signing key for each
invocation because it is not smart enough to remember them yet. `wheel
verify wheelfilename.whl` will check the signature for internal
consistentcy, but does not yet check that `RECORD` hashes to the correct
value, or that the files in the wheel hash to the values in `RECORD`.

See http://self-issued.info/docs/draft-ietf-jose-json-web-signature.html, http://self-issued.info/docs/draft-jones-json-web-signature-json-serialization-01.html

Slogans
-------

Wheel

* Because ‘newegg’ was taken.
* Python packaging - reinvented.
* A container for cheese.

.. toctree::
   :maxdepth: 2
   
   story

