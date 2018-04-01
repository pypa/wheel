from setuptools import setup

setup(name='simple.dist',
      version='0.1',
      description=u'A testing distribution \N{SNOWMAN}',
      packages=['simpledist'],
      extras_require={'voting': ['beaglevote']},
      )
