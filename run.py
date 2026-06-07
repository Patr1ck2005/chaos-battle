"""Quick start script for Chaos Battle server."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from server.main import main
    main()
