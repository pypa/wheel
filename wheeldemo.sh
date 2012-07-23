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

