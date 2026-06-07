"""Chaos Battle — entry point. Starts the HTTP + WebSocket server."""

import asyncio
import sys
import os

# Ensure the project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.network.server import run_server


def main():
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        print("\nServer stopped.")


if __name__ == "__main__":
    main()
