import io
import unittest
from unittest.mock import patch

import boukensha
from boukensha import ApiError, Context, Registry
from boukensha.repl import Repl


class FakeLogger:
    def __init__(self):
        self.turns = []

    def turn(self, *, n):
        self.turns.append(n)


class FakeAgent:
    instances = []
    outcomes = []

    def __init__(self, **kwargs):
        self.context = kwargs["context"]
        self.__class__.instances.append(self)

    def run(self):
        outcome = self.__class__.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        self.context.add_message("assistant", outcome)
        return outcome


class ReplTest(unittest.TestCase):
    def setUp(self):
        FakeAgent.instances = []
        FakeAgent.outcomes = []
        boukensha.loud()

    def make_repl(self, script):
        context = Context(system="system")
        registry = Registry(context)
        logger = FakeLogger()
        output = io.StringIO()
        repl = Repl(
            context=context,
            registry=registry,
            builder=object(),
            client=object(),
            logger=logger,
            provider="ollama",
            model="gemma4",
            version="0.8.0",
            input_stream=io.StringIO(script),
            output_stream=output,
            max_iterations=3,
            max_output_tokens=50,
        )
        return repl, context, logger, output

    def test_turns_use_fresh_agents_and_shared_history(self):
        repl, context, logger, output = self.make_repl(
            "first\nsecond\n/exit\n"
        )
        FakeAgent.outcomes = ["one", "two"]

        with patch("boukensha.repl.Agent", FakeAgent):
            repl.start()

        self.assertEqual(len(FakeAgent.instances), 2)
        self.assertIs(
            FakeAgent.instances[0].context,
            FakeAgent.instances[1].context,
        )
        self.assertEqual(logger.turns, [1, 2])
        self.assertEqual(
            [(message.role, message.content) for message in context.messages],
            [
                ("user", "first"),
                ("assistant", "one"),
                ("user", "second"),
                ("assistant", "two"),
            ],
        )
        self.assertIn("Goodbye.", output.getvalue())

    def test_commands_are_local_and_clear_resets_turn_number(self):
        repl, context, logger, output = self.make_repl(
            "\n/help\n/quiet\n/loud\nfirst\n/clear\nsecond\n/quit\n"
        )
        FakeAgent.outcomes = ["one", "two"]

        with patch("boukensha.repl.Agent", FakeAgent):
            repl.start()

        self.assertEqual(logger.turns, [1, 1])
        self.assertEqual(
            [(message.role, message.content) for message in context.messages],
            [("user", "second"), ("assistant", "two")],
        )
        rendered = output.getvalue()
        self.assertIn("Commands:", rendered)
        self.assertIn("conversation history cleared", rendered)

    def test_api_error_affects_only_one_turn(self):
        repl, context, logger, output = self.make_repl(
            "broken\nworking\n"
        )
        FakeAgent.outcomes = [ApiError("offline"), "recovered"]

        with patch("boukensha.repl.Agent", FakeAgent):
            repl.start()

        self.assertEqual(logger.turns, [1, 2])
        self.assertIn("[error] API call failed: offline", output.getvalue())
        self.assertIn("recovered", output.getvalue())

    def test_eof_exits_without_goodbye(self):
        repl, _context, logger, output = self.make_repl("")

        repl.start()

        self.assertEqual(logger.turns, [])
        self.assertNotIn("Goodbye.", output.getvalue())

    def test_banner_reports_server_counts_and_no_tool_state(self):
        repl, _context, _logger, output = self.make_repl("")
        repl.servers = {"mud": 26, "files": 4}
        repl.start()
        self.assertIn("servers:   mud (26)  files (4)", output.getvalue())

        repl, _context, _logger, output = self.make_repl("")
        repl.servers = {}
        repl.start()
        self.assertIn("none configured — the agent has no tools", output.getvalue())


if __name__ == "__main__":
    unittest.main()
