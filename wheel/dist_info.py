"""
Create a wheel (.whl) distribution.

A wheel is a built archive format.
"""

import os
import shutil

from setuptools.command.egg_info import egg_info


class dist_info(egg_info):

    description = 'create a .dist-info directory'

    def finalize_options(self):
        pass

    def run(self):
        egg_info = self.get_finalized_command('egg_info')
        egg_info.run()
        dist_info_dir = egg_info.egg_info[:-len('.egg-info')] + '.dist-info'

        bdist_wheel = self.get_finalized_command('bdist_wheel')
        bdist_wheel.egg2dist(egg_info.egg_info, dist_info_dir)

        if self.egg_base:
            shutil.move(dist_info_dir, os.path.join(
                self.egg_base, dist_info_dir))
