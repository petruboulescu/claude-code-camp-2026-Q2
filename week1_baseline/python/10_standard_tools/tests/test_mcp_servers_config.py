import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from boukensha import Config, Context, Registry
from boukensha.run_dsl import _register_mcp_servers
from boukensha.tools.mcp import CollisionError


class FakeClient:
    def __init__(self, count=2):
        self.tools = [{}] * count
        self.closed = False

    def close(self):
        self.closed = True


class McpServersConfigTest(unittest.TestCase):
    def config_from(self, text):
        temporary = tempfile.TemporaryDirectory()
        directory = Path(temporary.name)
        (directory / "settings.yaml").write_text(text, encoding="utf-8")
        patcher = patch.dict("os.environ", {"BOUKENSHA_DIR": str(directory)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(temporary.cleanup)
        return Config()

    def test_parses_entries_and_defaults(self):
        config = self.config_from(
            """
mcp_servers:
  mud:
    command: mud-manager
    args: [--mcp, 4000]
    prefix: tbamud
    env: {MUD_PORT: 4000}
  filesystem:
    command: npx
    required: false
"""
        )
        self.assertEqual(
            config.mcp_servers["mud"],
            {
                "command": "mud-manager",
                "args": ["--mcp", "4000"],
                "env": {"MUD_PORT": "4000"},
                "prefix": "tbamud",
                "required": True,
            },
        )
        self.assertFalse(config.mcp_servers["filesystem"]["required"])
        self.assertEqual(config.mcp_servers["filesystem"]["args"], [])

    def test_absent_and_structurally_invalid_blocks(self):
        self.assertEqual(self.config_from("tasks: {}").mcp_servers, {})
        with self.assertRaisesRegex(ValueError, "mcp_servers must be a mapping"):
            self.config_from("mcp_servers: []").mcp_servers
        with self.assertRaisesRegex(ValueError, "args must be a list"):
            self.config_from("mcp_servers: {bad: {args: nope}}").mcp_servers

    def test_required_failure_closes_earlier_clients(self):
        config = self.config_from(
            """
mcp_servers:
  first: {command: first}
  broken: {command: broken}
"""
        )
        first = FakeClient()

        def spawn(_registry, **entry):
            if entry["command"] == "broken":
                raise OSError("missing")
            return first

        with patch("boukensha.run_dsl.mcp_tools.register", side_effect=spawn):
            with self.assertRaisesRegex(RuntimeError, "'broken' failed to start"):
                _register_mcp_servers(Registry(Context()), config)
        self.assertTrue(first.closed)

    def test_optional_failure_warns_but_collision_is_fatal(self):
        optional = self.config_from(
            "mcp_servers: {decorative: {command: broken, required: false}}"
        )
        stderr = io.StringIO()
        with patch("boukensha.run_dsl.mcp_tools.register", side_effect=OSError("missing")):
            summary, clients = _register_mcp_servers(
                Registry(Context()), optional, stderr=stderr
            )
        self.assertEqual((summary, clients), ({}, []))
        self.assertIn("optional MCP server 'decorative'", stderr.getvalue())

        with patch(
            "boukensha.run_dsl.mcp_tools.register",
            side_effect=CollisionError("collision"),
        ):
            with self.assertRaises(CollisionError):
                _register_mcp_servers(Registry(Context()), optional)


if __name__ == "__main__":
    unittest.main()
