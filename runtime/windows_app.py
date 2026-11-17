"""Windows desktop entry point for the local-only AIBO Control Centre."""
import sys
from control_server import main

if __name__ == '__main__':
    if '--open-browser' not in sys.argv:
        sys.argv.append('--open-browser')
    main()
