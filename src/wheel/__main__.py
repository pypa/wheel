"""
Wheel command line tool (enable python -m wheel syntax)
"""

import sys


def main():
    """Runs the console script."""
    if __package__ == "":
        # To be able to run 'python wheel-0.9.whl/wheel':
        import os.path

        path = os.path.dirname(os.path.dirname(__file__))
        sys.path[0:0] = [path]

    from wheel import cli

    sys.exit(cli.main())


if __name__ == "__main__":
    sys.exit(main())
