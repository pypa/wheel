"""
Installation paths.

Map the .data/ subdirectory names to install paths.
"""

from distutils.command.install import install, SCHEME_KEYS

def get_install_paths(name):
    """
    Return the (distutils) install paths for the named dist.
    
    A dict with ('purelib', 'platlib', 'headers', 'scripts', 'data') keys.
    """
     # can't import up top due to monkeypatching
    from distutils.dist import Distribution

    paths = {}
    d = Distribution({'name':name})
    i = install(d)
    i.finalize_options()
    for key in SCHEME_KEYS:
        paths[key] = getattr(i, 'install_'+key)
    return paths
