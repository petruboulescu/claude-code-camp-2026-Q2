import asyncio
import tempfile
import unittest

from boukensha.context import Context
from boukensha.logger import Logger
from boukensha.repl import CommandResult
from boukensha.tui import ProgressState, Tui, context_severity, format_tokens, reduce_event


class FakeRepl:
    def __init__(self, logger):
        self.logger = logger
        self.context = Context(system="system")
        self.model = "test-model"
        self.version = "0.12.0"
        self.max_iterations = 7
        self.output = None
        self.commands = []

    def banner(self):
        return "Boukensha test banner"

    def on_output(self, callback):
        self.output = callback

    def handle_command(self, value):
        self.commands.append(value)
        if value in ("/exit", "/quit"):
            return CommandResult.QUIT
        if value.startswith("/"):
            if value == "/clear":
                self.context.clear_messages()
            return CommandResult.COMMAND
        return CommandResult.NOT_COMMAND

    def run_turn(self, value, cancel_event=None):
        self.logger.iteration(n=1, max=7)
        self.logger.response(text="done", usage={"input_tokens": 1200, "output_tokens": 5})
        self.output("done")


class TuiHelpersTest(unittest.TestCase):
    def test_token_formatting_and_event_reduction(self):
        self.assertEqual("999", format_tokens(999))
        self.assertEqual("1.2k", format_tokens(1200))
        state = reduce_event(ProgressState(), {"phase": "tool_call", "name": "look"})
        self.assertEqual("Calling tool: look", state.action)
        self.assertEqual(1, state.tool_calls)
        state = reduce_event(state, {"phase": "response", "usage": {"prompt_tokens": 12, "completion_tokens": 3}})
        self.assertEqual(12, state.session_input_tokens)
        self.assertEqual(3, state.turn_output_tokens)
        self.assertEqual("normal", context_severity(69))
        self.assertEqual("warning", context_severity(70))
        self.assertEqual("alert", context_severity(85))

    def test_headless_layout_mounts_all_four_zones(self):
        async def exercise():
            with tempfile.TemporaryDirectory() as directory:
                logger = Logger(dir=directory)
                app = Tui(FakeRepl(logger))
                try:
                    async with app.run_test(size=(80, 24)) as pilot:
                        await pilot.pause()
                        self.assertIsNotNone(app.query_one("#conversation"))
                        self.assertIsNotNone(app.query_one("#progress"))
                        self.assertIsNotNone(app.query_one("#input"))
                        self.assertIsNotNone(app.query_one("#status"))
                finally:
                    logger.close()
        asyncio.run(exercise())


if __name__ == "__main__":
    unittest.main()
