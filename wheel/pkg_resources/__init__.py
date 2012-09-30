# wheel's copy of pkg_resources. used for bootstrapping.

from __future__ import absolute_import
import sys

declared = []
def declare_namespace(package_name):
    declared.append(package_name)
declare_namespace.deferred = True

if sys.version_info[0] == 2:
    from .pkg_resources2 import *
else:
    from .pkg_resources3 import *

try:
    declare_namespace.deferred
    raise ImportError('pkg_resources import did not define declare_namespace')
except AttributeError:
    pass

while declared:
    # I'm not sure whether this will behave as required, since pkg_resources'
    # working_set has already iterated over all the distributions. It should
    # be more than enough for installs to work correctly.
    declare_namespace(declared.pop())
