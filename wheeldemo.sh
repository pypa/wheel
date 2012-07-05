#!/bin/sh
# bdist_wheel demo
# Create environment
virtualenv /tmp/wheeldemo
cd /tmp/wheeldemo

# Install wheel and patched pip, distribute
bin/pip install -e hg+https://bitbucket.org/dholth/wheel#egg=wheel hg+https://bitbucket.org/dholth/distribute#egg=distribute -e git+https://github.com/dholth/pip.git#egg=pip

# Download an unpack a package and its dependencies into build/
bin/pip install --build build --no-install --ignore-installed pyramid
cd build

# Make wheels for each package
for i in *; do (cd $i; /tmp/wheeldemo/bin/python setup.py bdist_wheel); done

# Copy them into a repository
mkdir ../wheelbase
find . -name *.whl -exec mv {} ../wheelbase \;
cd ..

# Remove build dir or pip will look there first
rm -rf build

# Install from saved wheels
bin/pip install -f file:///tmp/wheeldoc/wheelbase pyramid

