#!/usr/bin/env python3
"""Offline MCP handshake, discovery, prefix, and dispatch smoke demo."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boukensha import Context, Registry
from boukensha.tools.mcp import register


fixture = Path(__file__).parent.parent / "tests" / "fixtures" / "mcp_server.py"
context = Context(system="offline MCP demo")
registry = Registry(context)
client = register(
    registry,
    command=sys.executable,
    args=[fixture],
    env={"MCP_FIXTURE": "offline"},
    prefix="demo",
)
try:
    print(f"server: {client.server_info}")
    print(f"tools:  {', '.join(registry.tool_names)}")
    print(f"look:   {registry.dispatch('demo__look')}")
    print("[offline MCP demo OK]")
finally:
    client.close()
