"""A deliberately small MCP-over-stdio client."""

from __future__ import annotations

from collections import deque
import json
import os
import subprocess
import threading

from ..version import VERSION


class McpError(RuntimeError):
    """Raised when an MCP subprocess or protocol exchange fails."""


class Client:
    PROTOCOL_VERSION = "2025-06-18"

    @classmethod
    def spawn(cls, *, command, args=None, env=None):
        return cls(command=command, args=args, env=env)

    def __init__(self, *, command, args=None, env=None):
        command = str(command)
        if not command:
            raise McpError("MCP server command is empty")

        argv = [command, *(str(value) for value in (args or []))]
        child_env = os.environ.copy()
        child_env.update({str(key): str(value) for key, value in (env or {}).items()})
        self._process = None
        self._id = 0
        self._closed = False
        self._stderr_tail = deque(maxlen=20)
        self._stderr_thread = None

        try:
            self._process = subprocess.Popen(
                argv,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                env=child_env,
            )
            self._stderr_thread = threading.Thread(
                target=self._drain_stderr,
                name="boukensha-mcp-stderr",
                daemon=True,
            )
            self._stderr_thread.start()
            self._handshake()
            response = self._request("tools/list")
            result = response.get("result") or {}
            tools = result.get("tools", [])
            if not isinstance(tools, list):
                raise McpError("tools/list returned a non-list tools value")
            self.tools = tools
        except Exception as error:
            self.close()
            if isinstance(error, McpError):
                raise
            raise McpError(f"could not start MCP server {command!r}: {error}") from error

    def call_tool(self, name, arguments=None):
        response = self._request(
            "tools/call",
            {"name": str(name), "arguments": arguments or {}},
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpError("tools/call returned no result")
        content = result.get("content") or []
        if not isinstance(content, list):
            raise McpError("tools/call returned invalid content")
        text = "\n".join(
            block["text"]
            for block in content
            if isinstance(block, dict)
            and block.get("type") == "text"
            and isinstance(block.get("text"), str)
        )
        return {"text": text, "error": bool(result.get("isError"))}

    def close(self):
        if self._closed:
            return
        self._closed = True
        process = self._process
        if process is None:
            return

        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass
        if self._stderr_thread is not None:
            self._stderr_thread.join(timeout=1)

    def __enter__(self):
        return self

    def __exit__(self, _type, _value, _traceback):
        self.close()

    def _handshake(self):
        response = self._request(
            "initialize",
            {
                "protocolVersion": self.PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "boukensha", "version": VERSION},
            },
        )
        result = response.get("result")
        if not isinstance(result, dict):
            raise McpError("initialize returned no result")
        self.server_info = result.get("serverInfo")
        self._notify("notifications/initialized")

    def _request(self, method, params=None):
        self._id += 1
        request_id = self._id
        self._write(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        while True:
            message = self._read_message(method)
            if message.get("id") != request_id:
                continue
            if "error" in message:
                raise McpError(f"{method} failed: {message['error']!r}")
            if "result" not in message:
                raise McpError(f"{method} returned neither result nor error")
            return message

    def _notify(self, method, params=None):
        self._write({"jsonrpc": "2.0", "method": method, "params": params or {}})

    def _write(self, message):
        process = self._process
        if self._closed or process is None or process.stdin is None:
            raise McpError("MCP server connection is closed")
        try:
            process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
            process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as error:
            raise McpError(f"could not write to MCP server: {error}") from error

    def _read_message(self, method):
        process = self._process
        if process is None or process.stdout is None:
            raise McpError("MCP server has no stdout pipe")
        line = process.stdout.readline()
        if line == "":
            detail = "".join(self._stderr_tail).strip()
            suffix = f": {detail}" if detail else ""
            raise McpError(f"MCP server closed during {method}{suffix}")
        if not line.strip():
            return self._read_message(method)
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            raise McpError(f"invalid JSON during {method}: {error.msg}") from error
        if not isinstance(message, dict):
            raise McpError(f"invalid JSON-RPC message during {method}")
        return message

    def _drain_stderr(self):
        process = self._process
        if process is None or process.stderr is None:
            return
        try:
            for line in process.stderr:
                self._stderr_tail.append(line)
        except (OSError, ValueError):
            pass
