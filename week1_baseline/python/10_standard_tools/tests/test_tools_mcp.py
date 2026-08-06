import unittest

from boukensha import Context, Registry
from boukensha.tools.mcp import CollisionError, prefixed, register_client


class FakeClient:
    def __init__(self):
        self.tools = [
            {
                "name": "move",
                "description": "Move",
                "inputSchema": {
                    "properties": {
                        "direction": {
                            "description": "Direction",
                            "enum": ["north", "south"],
                        }
                    }
                },
            }
        ]
        self.calls = []

    def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        is_error = arguments.get("direction") == "sideways"
        return {"text": "bad" if is_error else "moved", "error": is_error}


class McpToolsTest(unittest.TestCase):
    def test_registration_maps_schema_prefix_and_remote_name(self):
        context = Context()
        registry = Registry(context)
        client = FakeClient()
        count = register_client(registry, client, prefix="mud")

        self.assertEqual(count, 1)
        self.assertEqual(prefixed("move", "mud"), "mud__move")
        parameter = context.tools["mud__move"].parameters["direction"]
        self.assertEqual(parameter["type"], "string")
        self.assertIn("one of: north, south", parameter["description"])
        self.assertEqual(
            registry.dispatch("mud__move", {"direction": "north"}),
            "moved",
        )
        self.assertEqual(client.calls, [("move", {"direction": "north"})])

    def test_tool_error_becomes_agent_visible_text(self):
        context = Context()
        registry = Registry(context)
        register_client(registry, FakeClient())
        self.assertEqual(
            registry.dispatch("move", {"direction": "sideways"}),
            "error: bad",
        )

    def test_collision_names_prefix_fix(self):
        context = Context()
        registry = Registry(context)
        registry.tool("move", description="local", func=lambda: "local")
        with self.assertRaisesRegex(CollisionError, "collision on 'move'.*prefix"):
            register_client(registry, FakeClient())


if __name__ == "__main__":
    unittest.main()
