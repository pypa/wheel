from setuptools import setup

setup(name='simple.dist',
      version='0.1',
      description='A testing distribution.',
      packages=['simpledist'],
      extras_require={'voting': ['beaglevote']},
      )

