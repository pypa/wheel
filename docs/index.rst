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
software. When you are creating a virtualenv for each revision of your
software, the savings can be dramatic. This example packages pyramid
and all its dependencies as wheels, and then installs pyramid from the
built packages::

        # Install pip, wheel
        pip install git+https://github.com/dholth/pip#egg=pip wheel

        # Build a directory of wheels
        mkdir /tmp/wheel-cache
        pip install --wheel-cache=/tmp/wheel-cache --no-install pyramid
        
        # Install from cached wheels
        pip install --use-wheel --no-index --find-links=file:///tmp/wheel-cache pyramid

For lxml, an up to 3-minute "search for the newest version and compile"
can become a less-than-1 second "unpack from wheel".

File Contents
-------------

Wheel files contain a folder `{distribution}-{version}.dist-info/` with
the PEP 376 metadata and an additional file `WHEEL` with metadata about
the package itself.

The root of a .whl is either purelib or platlib.

If a .whl contains scripts, both purelib and platlib, or any
other files that are not installed on sys.path, they are found in
`{distribution}-{version}.data/{key}`.

Wheel files contain metadata about the wheel format itself in
`{distribution}-{version}/WHEEL` ::

        Wheel-Version: 0.9
        Packager: bdist_wheel
        Root-Is-Purelib: true

A wheel installer should warn if `Wheel-Version` is greater than the
version it supports, and fail if `Wheel-Version` has a greater major
version than the version it supports.

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
	
For example, package-1.0-py27-none-any.whl is compatible with Python 2.7
(any Python 2.7 implementation) on any CPU architecture.

The last three components of the file are called "compatibility tags."  The
compatibility tags express the package's basic interpreter requirements, and
are detailed in PEP 485 [http://hg.python.org/peps/file/tip/pep-0425.txt]. 

Ranking wheels with the same version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Installers will sometimes have to choose the best wheel among
several for the same version of a distribution. First, rank the
supported implementation tags by preference, e.g. CPython might
prefer cp33m, py33, py32. Second, choose the wheel with the smallest
arity (``len(python_tag.split('.')) * len(abi_tag.split('.')) *
len(platform_tag.split('.'))``). If all else fails, rebuild from source.

Automatically sign wheel files
------------------------------

`python setup.py bdist_wheel` will automatically sign wheel files if
the environment variable `WHEEL_TOOL` is set to the path of the `wheel`
command line tool::

	# Install the wheel tool and its dependencies
	$ pip install wheel[tool]
	# Generate a signing key (only once)
	$ wheel keygen
	    
	$ export WHEEL_TOOL=/path/to/wheel	
	$ python setup.py bdist_wheel
	
Signing is done in a subprocess because it is not convenient for 
the build environment to contain bindings to the keyring and 
cryptography libraries.

A future version of `wheel sign` will be able to choose different signing
keys depending on the package name, in case a user wishes to reserve a more
widely trusted key for packages they intend to distribute.

Signed wheel files
------------------

Wheel files include an extended RECORD that enables
digital signatures. PEP 376’s RECORD is altered to include
``digestname=urlsafe_b64encode_nopad(digest)`` (urlsafe base64 encoding
with no trailing = characters) as the second column instead of an
md5sum. All possible entries are hashed, including .pyc and other
generated files, but not RECORD. For example::

        file.py,sha256=AVTFPZpEKzuHr7OvQZmhaU3LvwKz06AJw8mT_pNh2yI,3144
        distribution-1.0.dist-info/RECORD,,

RECORD.jws is not mentioned in RECORD at all. Every other file in the
archive must have a correct sha256 digest in RECORD, or the ``wheel
unpack`` command will fail.

The signature is one or more JSON Web Signature JSON Serialization
(JWS-JS) signatures stored in a file RECORD.jws adjacent to RECORD.

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
the extra ``ed25519=(key)`` with no associated dependencies.

Key distribution is outside the scope of this spec. Public wheel signing
keys could be signed with the packager’s GPG key, or stored at an
https://-protected URL.

The `wheel` command line tool can create signed wheel files with
``wheel sign wheelfile.whl``. ``wheel verify wheelfile.whl`` checks
the signatures for internal consistency and lists the decoded signature
headers and payloads. ``wheel unpack wheelfile.whl`` extracts the archive
and verifies the sha256 hashes of each file. ``wheel keygen`` creates
a keypair, remembers the signing key with the Python keyring library,
and remembers that you trust the key in a platform-specific location;
on Linux, ``~/.config/wheel/wheel.json``.

JSON Web Signatures Extensions
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The Ed25519 algorithm is used as an extension to the JSON Web Signatures
specification. Wheel uses ``alg="Ed25519"`` in the header. The ``key``
attribute holds the signature's public JSON Web Key. For JSON Web Key /
JSON Private Key the verifying (public) key is called ``vk`` and the
signing (private) key is called ``sk``.

Example header::

    {
      "alg": "Ed25519", 
      "typ": "JWT", 
      "key": {
        "alg": "Ed25519", 
        "vk": "tmAYCrSfj8gtJ10v3VkvW7jOndKmQIYE12hgnFu3cvk"
      }
    }

A future version of wheel may omit ``typ``.

Example payload::

    { "hash": "sha256=ADD-r2urObZHcxBW3Cr-vDCu5RJwT4CaRTHiFmbcIYY" }

A future version of wheel may include timestamps in the payload or in
the signature.

See http://self-issued.info/docs/draft-ietf-jose-json-web-signature.html,
http://self-issued.info/docs/draft-jones-json-web-signature-json-serialization-01.html,
http://self-issued.info/docs/draft-ietf-jose-json-web-key-05.html,
http://self-issued.info/docs/draft-jones-jose-json-private-key-00.html


Slogans
-------

Wheel

* Because ‘newegg’ was taken.
* Python packaging - reinvented.
* A container for cheese.

.. toctree::
   :maxdepth: 2
   
   story

