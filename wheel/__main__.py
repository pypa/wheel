"""
Wheel command line tool (enable python -m wheel syntax)
"""

def main(): # needed for console script
    import wheel.tool
    wheel.tool.main()

if __name__ == "__main__":
    main()
