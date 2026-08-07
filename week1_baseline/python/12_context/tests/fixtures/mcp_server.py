#!/usr/bin/env python3
"""Tiny deterministic JSON-RPC stdio server used only by offline tests."""

import json
import os
import sys


TOOLS = [
    {
        "name": "look",
        "description": "Look around",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "move",
        "description": "Move somewhere",
        "inputSchema": {
            "type": "object",
            "properties": {
                "direction": {
                    "type": "string",
                    "description": "Direction to travel",
                    "enum": ["north", "south"],
                }
            },
        },
    },
]


def send(message):
    print(json.dumps(message), flush=True)


for line in sys.stdin:
    message = json.loads(line)
    method = message.get("method")
    if method == "notifications/initialized":
        continue
    request_id = message["id"]
    if method == "initialize":
        send({"jsonrpc": "2.0", "method": "fixture/notice", "params": {}})
        send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": message["params"]["protocolVersion"],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "fixture", "version": "1.0"},
                },
            }
        )
    elif method == "tools/list":
        send({"jsonrpc": "2.0", "id": 9999, "result": {}})
        send({"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}})
    elif method == "tools/call":
        name = message["params"]["name"]
        arguments = message["params"]["arguments"]
        if name == "move" and arguments.get("direction") == "sideways":
            result = {
                "content": [{"type": "text", "text": "invalid direction"}],
                "isError": True,
            }
        else:
            result = {
                "content": [
                    {"type": "image", "data": "ignored"},
                    {
                        "type": "text",
                        "text": f"{name}:{json.dumps(arguments, sort_keys=True)}",
                    },
                    {"type": "text", "text": os.environ.get("MCP_FIXTURE", "")},
                ]
            }
        send({"jsonrpc": "2.0", "id": request_id, "result": result})
    else:
        send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32601, "message": "unknown method"},
            }
        )
