"""
wheel command line tool.
"""

import sys
import cmdln

class WheelTool(cmdln.Cmdln):
    name = "wheel"
    def do_install(self, subcmd, opts, *wheels):
        """${cmd_name}: Install a wheel"""
        raise NotImplementedError()

if __name__ == "__main__":
    wheel = WheelTool()
    sys.exit(wheel.main())
