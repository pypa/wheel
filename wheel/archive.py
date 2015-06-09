"""
Archive tools for wheel.
"""

import time
import logging
import os.path
import zipfile

log = logging.getLogger("wheel")


def archive_wheelfile(base_name, base_dir):
    '''Archive all files under `base_dir` in a whl file and name it like
    `base_name`.
    '''
    olddir = os.path.abspath(os.curdir)
    base_name = os.path.abspath(base_name)
    try:
        os.chdir(base_dir)
        return make_wheelfile_inner(base_name)
    finally:
        os.chdir(olddir)


def make_wheelfile_inner(base_name, base_dir='.'):
    """Create a whl file from all the files under 'base_dir'.

    Places .dist-info at the end of the archive."""

    zip_filename = base_name + ".whl"

    log.info("creating '%s' and adding '%s' to it", zip_filename, base_dir)

    # XXX support bz2, xz when available
    zip = zipfile.ZipFile(open(zip_filename, "wb+"), "w",
                          compression=zipfile.ZIP_DEFLATED)

    score = {'WHEEL': 1, 'METADATA': 2, 'RECORD': 3}
    deferred = []

    def writefile(path):
        zip.write(path, path)
        log.info("adding '%s'" % path)

    for dirpath, dirnames, filenames in os.walk(base_dir):
        for name in filenames:
            path = os.path.normpath(os.path.join(dirpath, name))

            if os.path.isfile(path):
                if dirpath.endswith('.dist-info'):
                    deferred.append((score.get(name, 0), path))
                else:
                    writefile(path)

    deferred.sort()
    for score, path in deferred:
        writefile(path)

    # Before we close the zip file, see if the caller is forcing the timestamp
    # of the individual TarInfo objects.  See issue #143.
    timestamp = os.environ.get('WHEEL_FORCE_TIMESTAMP')
    if timestamp is not None:
        date_time = time.localtime(int(timestamp))[0:6]
        for info in zip.infolist():
            info.date_time = date_time

    zip.close()

    return zip_filename
