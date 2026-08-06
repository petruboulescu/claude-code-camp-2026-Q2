import threading
import unittest

from boukensha import Agent, ApiError, Context, Registry
from boukensha.errors import TurnCancelled


class FakeLogger:
    def __getattr__(self, name):
        return lambda **kwargs: None


class FakeBackend:
    model = "fake"


class FakeBuilder:
    backend = FakeBackend()

    @staticmethod
    def parse_response(response):
        return response


class SequenceClient:
    def __init__(self, responses):
        self.responses = iter(responses)

    def call(self, **kwargs):
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return response


def response(text):
    return {
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
    }


def tool_response():
    return {
        "content": [
            {
                "type": "tool_use",
                "id": "tool-1",
                "name": "missing",
                "input": {},
            }
        ],
        "stop_reason": "tool_use",
    }


class AgentHistoryTest(unittest.TestCase):
    def make_agent(self, responses, *, max_iterations=2):
        context = Context(system="system")
        return context, Agent(
            context=context,
            registry=Registry(context),
            builder=FakeBuilder(),
            client=SequenceClient(responses),
            logger=FakeLogger(),
            max_iterations=max_iterations,
        )

    def test_terminal_response_is_added_to_history(self):
        context, agent = self.make_agent([response("finished")])

        self.assertEqual(agent.run(), "finished")
        self.assertEqual(context.messages[-1].role, "assistant")
        self.assertEqual(context.messages[-1].content, "finished")

    def test_wrap_up_response_is_added_to_history(self):
        context, agent = self.make_agent(
            [tool_response(), response("summary")],
            max_iterations=1,
        )

        self.assertEqual(agent.run(), "summary")
        self.assertEqual(context.messages[-1].role, "assistant")
        self.assertEqual(context.messages[-1].content, "summary")

    def test_wrap_up_api_fallback_is_added_to_history(self):
        context, agent = self.make_agent(
            [tool_response(), ApiError("offline")],
            max_iterations=1,
        )

        result = agent.run()

        self.assertIn("action limit", result)
        self.assertEqual(context.messages[-1].role, "assistant")
        self.assertEqual(context.messages[-1].content, result)

    def test_clear_messages_retains_system_and_tools(self):
        context = Context(system="system")
        registry = Registry(context)
        registry.tool(
            "echo",
            description="Echo",
            func=lambda value: value,
        )
        context.add_message("user", "hello")

        context.clear_messages()

        self.assertEqual(context.messages, [])
        self.assertEqual(context.system, "system")
        self.assertIn("echo", context.tools)

    def test_pre_cancelled_turn_never_calls_provider(self):
        context = Context(system="system")
        cancelled = threading.Event()
        cancelled.set()
        agent = Agent(
            context=context,
            registry=Registry(context),
            builder=FakeBuilder(),
            client=SequenceClient([response("should not run")]),
            logger=FakeLogger(),
            cancel_event=cancelled,
        )
        with self.assertRaises(TurnCancelled):
            agent.run()
        self.assertEqual([], context.messages)


if __name__ == "__main__":
    unittest.main()
