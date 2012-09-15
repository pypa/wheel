"""
Wheel command line tool (enable python -m wheel syntax)
"""

def main(): # needed for console script
    if __package__ == '':
        # To be able to run 'python wheel-0.9.whl/wheel':
        import sys
        import os.path
        path = os.path.dirname(os.path.dirname(__file__))
        sys.path[0:0] = [path]
    import wheel.tool
    wheel.tool.main()

if __name__ == "__main__":
    main()
