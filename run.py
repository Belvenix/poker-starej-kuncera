#!/usr/bin/env python3
"""Start the Poker Starej Kuncery server."""
import asyncio
import sys

# Allow running from project root
sys.path.insert(0, ".")

from server.server import main

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8000
    asyncio.run(main(host, port))
