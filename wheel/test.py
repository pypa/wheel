import os

from nose.tools import assert_true, assert_false, assert_equal, raises
from .install import WheelFile

def test_findable():
    """Make sure pkg_resources can find us."""
    import pkg_resources
    assert pkg_resources.working_set.by_key['wheel'].version

def test_wheel():
    for filename in os.listdir(os.getenv('WHEELBASE')):
        print filename
        
def test_markers():
    from .markers import interpret, default_environment, as_function
    
    os_name = os.name
    
    assert_true(interpret("os.name != 'buuuu'"))
    assert_true(interpret("python_version > '1.0'"))
    assert_true(interpret("python_version < '5.0'"))
    assert_true(interpret("python_version <= '5.0'"))
    assert_true(interpret("python_version >= '1.0'"))
    assert_true(interpret("'%s' in os.name" % os_name))
    assert_true(interpret("'buuuu' not in os.name"))
    
    assert_false(interpret("os.name == 'buuuu'"))
    assert_false(interpret("python_version < '1.0'"))
    assert_false(interpret("python_version > '5.0'"))
    assert_false(interpret("python_version >= '5.0'"))
    assert_false(interpret("python_version <= '1.0'"))
    assert_false(interpret("'%s' not in os.name" % os_name))
    assert_false(interpret("'buuuu' in os.name and python_version >= '5.0'"))
    
    environment = default_environment()
    environment['extra'] = 'test'
    assert_true(interpret("extra == 'test'", environment))
    assert_false(interpret("extra == 'doc'", environment))
    
    @raises(NameError)
    def raises_nameError():
        interpret("python.version == '42'")
    
    raises_nameError()
    
    @raises(SyntaxError)
    def raises_syntaxError():
        interpret("(x for x in (4,))")
        
    raises_syntaxError()
    
    statement = "python_version == '5'"
    assert_equal(as_function(statement).__doc__, statement)
    