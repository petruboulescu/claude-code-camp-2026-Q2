#!/usr/bin/env python3
"""Step 10: all automatic tools arrive from configured MCP servers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boukensha


config = boukensha.config()
print(f"Config:  {config}")
print(f"Servers: {', '.join(config.mcp_servers)}")
print()

boukensha.run(
    task=(
        "Look at your surroundings, check your score, then inspect the "
        "available exits and tell me what you see."
    )
)
