"""Interpret PEP 345 environment markers.

EXPR [in|==|!=|not in] EXPR [or|and] ...

where EXPR belongs to any of those:

    python_version = '%s.%s' % (sys.version_info[0], sys.version_info[1])
    python_full_version = sys.version.split()[0]
    os.name = os.name
    sys.platform = sys.platform
    platform.version = platform.version()
    platform.machine = platform.machine()
    platform.python_implementation = platform.python_implementation()
    a free string, like '2.4', or 'win32'
"""

import ast
import os
import platform
import sys

from ast import NodeTransformer
from platform import python_implementation

# restricted set of variables
_VARS = {'sys.platform': sys.platform,
         'python_version': '%s.%s' % sys.version_info[:2],
         # FIXME parsing sys.platform is not reliable, but there is no other
         # way to get e.g. 2.7.2+, and the PEP is defined with sys.version
         'python_full_version': sys.version.split(' ', 1)[0],
         'os.name': os.name,
         'platform.version': platform.version(),
         'platform.machine': platform.machine(),
         'platform.python_implementation': python_implementation(),
         'extra': None # wheel extension
        }

def default_environment():
    """Return copy of default PEP 385 globals dictionary."""
    return dict(_VARS)

class ASTWhitelist(NodeTransformer):
    def __init__(self, statement):
        self.statement = statement # for error messages
    
    ALLOWED = (ast.Compare, ast.BoolOp, ast.Attribute, ast.Name, ast.Load,
        ast.Str, ast.cmpop, ast.boolop)
    
    def visit(self, node):
        """Ensure statement only contains allowed nodes."""
        if not isinstance(node, self.ALLOWED):
            raise SyntaxError('%s not allowed\n%s\n%s' %
                              (node.__class__, 
                               self.statement, 
                               (' ' * node.col_offset) + '^'))
        return NodeTransformer.visit(self, node)
    
    def visit_Attribute(self, node):
        """Flatten one level of attribute access."""
        new_node = ast.Name("%s.%s" % (node.value.id, node.attr), node.ctx)
        return ast.copy_location(new_node, node)

def parse_marker(marker):
    tree = ast.parse(marker, mode='eval')
    new_tree = ASTWhitelist(marker).generic_visit(tree)
    return new_tree

def compile_marker(parsed_marker):
    return compile(parsed_marker, '<environment marker>', 'eval',
                   dont_inherit=True)

def as_function(marker):
    """Return compiled marker as a function accepting an environment dict."""
    if not marker.strip():
        def dummy_marker(environment=None, override=None):
            """"""
            return True
        return dummy_marker        
    compiled_marker = compile_marker(parse_marker(marker))
    def marker_fn(environment=None, override=None):
        """Extra updates environment"""
        if override is None:
            override = {}
        if environment is None:
            environment = default_environment()
        environment.update(override)
        return eval(compiled_marker, environment)
    marker_fn.__doc__ = marker
    return marker_fn

def interpret(marker, environment=None):
    return as_function(marker)(environment)
