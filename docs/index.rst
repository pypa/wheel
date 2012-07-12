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

The wheel project provides a `bdist_wheel` command
for setuptools (requiring a patched distribute from
https://bitbucket.org/dholth/distribute). Wheel files can be installed
with a patched `pip` from https://github.com/dholth/pip.

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
software, as in some web deployment schemes, the savings can be dramatic::

        #!/bin/sh
        # bdist_wheel demo
        # Create environment
        virtualenv /tmp/wheeldemo
        cd /tmp/wheeldemo
        source bin/activate

        # Install wheel and patched pip, distribute
        bin/pip install -e hg+https://bitbucket.org/dholth/wheel#egg=wheel \
                hg+https://bitbucket.org/dholth/distribute#egg=distribute \                
                -e git+https://github.com/dholth/pip.git#egg=pip

        # Download and unpack a package and its dependencies into build/
        bin/pip install --build build --no-install --ignore-installed pyramid

        # Make wheels for each package
        for i in build/*; do (cd $i; python setup.py bdist_wheel); done

        # Copy them into a repository
        mkdir ../wheelbase
        find . -name *.whl -exec mv {} ../wheelbase \;
        cd ..

        # Remove build dir or pip will look there first
        rm -rf build


        # Install from saved wheels
        bin/pip install -f file:///tmp/wheeldoc/wheelbase pyramid

File name convention
--------------------

The wheel filename is `{distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl` ::

    distribution: Distribution name, e.g. ‘django’, ‘pyramid’
    version: PEP 386-compliant version, e.g. 1.0
    build tag: Optional build number. Must start with a digit. A tie breaker if two wheels have the same version.
    Python implementation tag ‘pp27’
    Python abi tag ‘pp18’
    Platform tag

For example, package-1.0-py27-noabi-noarch.whl is compatible with Python 2.7 (any Python 2.7 implementation) on any CPU architecture.

File Contents
-------------

Wheel files contain a folder `{distribution}-{version}.dist-info/` with the PEP 376 metadata and an additional file `WHEEL` with metadata about the package itself.

The root of a .whl is either purelib or platlib.

If a .whl contains scripts, both purelib and platlib, or any other files that are not installed on sys.path, they are found in `{distribution}-{version}.data/{key}`.

Wheel files contain metadata about the wheel format itself in `{distribution}-{version}/WHEEL` ::

        Wheel-Version: 0.9
        Packager: bdist_wheel-0.1
        Root-Is-Purelib: true

Values used in wheel filenames
------------------------------

The Python implementation is abbreviated. Each implementation has a two-letter code :

* py: Generic Python
* cp: CPython
* ip: IronPython
* pp: PyPy
* jy: Jython

concatenated with py_version_nodot “27”.

The ABI tag is an abbreviated SOABI “cp33m”, or, for “pure Python” packages, “noabi”

The platform tag is distutils.util.get_platform() with all periods and hyphens replaced with underscore, or the string ‘noarch’.

Wheels within wheels XXX work in progress
-----------------------------------------

A wheel filename can contain multiple implementation, platform, and
architecture tags separated by a `.` to indicate compatibility.

Two or more wheel files may be combined into a multi-wheel

* Ensure both wheel’s Root-Is-Purelib flags match.
* Merge the two directory trees, taking care that any overlapping files have the same content (Python source code) or can be merged sensibly (fat binaries, potentially METADATA). This will not always be possible.
* For each source wheel, copy RECORD into RECORD.{python tag}.{platform tag}.
* Create a new RECORD listing the combined contents of the multi-wheel.

The multi-wheel filename indicates the sets of Python versions and platforms from the source wheels:

`{distribution}-{version}-{python tag 1}.{python tag 2}-{platform tag 1}.{platform tag 2}.whl`

(The single Python and platform tags from an ordinary wheel become
.-separated sets of tags.) The multi-wheel is only legal if it is
compatible with the Cartesian product of the two sets of tags; normally,
one of {python tag} or {platform tag} willl match when combining two
wheels into a multi-wheel.

For example, a mostly-Python project with a .so extension module on Linux
and a .dll on Windows could save server space and simplify its download
page by combining multiple builds into a multi-wheel:

mostlypython-1.0-cp33-cp33m-win32.whl + mostlypython-1.0-cp33-cp33m-linux_x86_64.whl = mostlypython-1.0-cp33-cp33m-linux_x86_64.win32.whl

Ranking multi-wheels with the same version
::::::::::::::::::::::::::::::::::::::::::

Installers will sometimes have to choose the best wheel among several
for the same version of a distribution. First, rank the supported
implementation tags by preference, e.g. CPython might prefer cp33m,
py33, py32. Second, choose the multi-wheel with the smallest arity. If
all else fails, rebuild from source.

Signed wheel files
------------------

Wheel files include an extended RECORD that enables
digital signatures. PEP 376’s RECORD is altered to include
digestname=urlsafe_b64encode_nopad(digest) (base64 encoding with no
trailing = characters) as the second column instead of an md5sum. All
possible entries are hashed, including .pyc and other generated files,
but not RECORD. For example::

        file.py,sha256=AVTFPZpEKzuHr7OvQZmhaU3LvwKz06AJw8mT_pNh2yI,3144

The signature is a JSON Web Signature token stored in a file
RECORD.JWT in the .dist-info directory adjacent to RECORD. The JSON Web
Signature payload is an object with one key “hash” with a value
of a hash of RECORD stored in the same format as entries in RECORD:
digestname=urlsafe_b64encode_nopad(digest), but need not use the same hash
function as RECORD. The signing algorithm ‘JWS using HMAC SHA-256’
must be supported. *May switch to json web signature serialization format
to support multiple signatures.*

To verify, first verify the signature, then hash RECORD with the hashing
algorithm used in the signed payload and check for equality with the
signed payload, and finally verify that all the files contained in RECORD
actually hash to the values listed in RECORD.

Remember that files can be included in the wheel file without being
included in the signed RECORD; an implementation could choose to unpack
only the verified files. Verification must also reject signatures that
use hashing algorithms outside a list of trusted algorithms.

Key distribution is outside the scope of this spec. Public wheel signing
keys could be signed with the packager’s GPG key, or stored at an
https://-protected URL. Within an organization, wheel files could be
signed with a private key using HMAC and distribute the private key
over ssh.

See http://self-issued.info/docs/draft-ietf-jose-json-web-signature.html

Slogans
-------

Wheel

* Because ‘newegg’ was taken.
* Python packaging - reinvented.
* A container for cheese.

.. toctree::
   :maxdepth: 2

