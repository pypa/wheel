#!/bin/sh
# Vendorize pkg_resources and _markerlib from ../distribute/

cp ../pep425/pep425tags.py wheel

cp ../distribute/_markerlib/markers.py wheel/pkg_resources/markerlib.py
cp ../distribute/pkg_resources.py wheel/pkg_resources/pkg_resources2.py
2to3 ../distribute/pkg_resources.py -w -n -o wheel/pkg_resources
mv wheel/pkg_resources/pkg_resources.py wheel/pkg_resources/pkg_resources3.py


