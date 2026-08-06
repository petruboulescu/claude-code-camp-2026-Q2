import sys
import unittest
from pathlib import Path

from boukensha.mcp import Client, McpError


FIXTURE = Path(__file__).parent / "fixtures" / "mcp_server.py"


class McpClientTest(unittest.TestCase):
    def setUp(self):
        self.client = None

    def tearDown(self):
        if self.client is not None:
            self.client.close()

    def spawn(self):
        self.client = Client.spawn(
            command=sys.executable,
            args=[FIXTURE],
            env={"MCP_FIXTURE": 4000},
        )
        return self.client

    def test_handshake_discovers_tools_and_ignores_unrelated_messages(self):
        client = self.spawn()
        self.assertEqual(client.server_info["name"], "fixture")
        self.assertEqual([tool["name"] for tool in client.tools], ["look", "move"])

    def test_call_tool_joins_text_and_passes_environment(self):
        result = self.spawn().call_tool("look", {"room": 3})
        self.assertEqual(result, {"text": 'look:{"room": 3}\n4000', "error": False})

    def test_tool_error_is_data(self):
        result = self.spawn().call_tool("move", {"direction": "sideways"})
        self.assertEqual(result, {"text": "invalid direction", "error": True})

    def test_missing_command_is_wrapped_and_close_is_idempotent(self):
        with self.assertRaisesRegex(McpError, "could not start MCP server"):
            Client.spawn(command="boukensha-no-such-mcp-server-xyz")
        client = self.spawn()
        client.close()
        client.close()
        self.assertIsNotNone(client._process.returncode)


if __name__ == "__main__":
    unittest.main()
