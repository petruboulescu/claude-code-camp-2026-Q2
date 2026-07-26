import json
import tempfile
import unittest
from pathlib import Path

import boukensha
from boukensha import Agent, Context, Logger, PLAYER


class FakeBackend:
    model = "priced-model"
    usage_unit = "tokens"
    usage_level = "response"

    def estimate_cost(self, *, input_tokens, output_tokens):
        return (input_tokens + output_tokens) / 1_000_000


class FakeBuilder:
    backend = FakeBackend()

    @staticmethod
    def parse_response(response):
        return response["parsed"]


class FakeClient:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def call(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.responses)


class FailingRegistry:
    @staticmethod
    def dispatch(name, args):
        raise ValueError("broken")


def response(stop_reason, content, **extra):
    return {
        **extra,
        "stop_reason": stop_reason,
        "parsed": {
            "stop_reason": stop_reason,
            "content": content,
        },
    }


class LoggerTest(unittest.TestCase):
    def setUp(self):
        boukensha._debug = False
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def events(self, logger):
        logger.close()
        return [
            json.loads(line)
            for line in logger.path.read_text(encoding="utf-8").splitlines()
        ]

    def test_session_metadata_cost_and_debug_gate(self):
        logger = Logger(
            dir=self.temp_dir.name,
            session_id="test",
            snapshot={"version": 6},
        )
        logger.response(
            text=" done ",
            usage={"prompt_tokens": "10", "completion_tokens": 2},
            task=PLAYER,
            backend=FakeBackend(),
        )
        logger.raw(data={"hidden": True})
        boukensha.debug()
        logger.raw(data={"shown": True})

        events = self.events(logger)

        self.assertEqual(
            [event["phase"] for event in events],
            ["session_start", "response", "raw"],
        )
        self.assertEqual(events[0]["version"], 6)
        self.assertEqual(events[1]["text"], "done")
        self.assertEqual(events[1]["task"], "player")
        self.assertEqual(events[1]["provider"], "fake_backend")
        self.assertEqual(events[1]["input_tokens"], 10)
        self.assertEqual(events[1]["output_tokens"], 2)
        self.assertEqual(events[1]["cost_usd"], 0.000012)
        self.assertEqual(events[2]["data"], {"shown": True})
        self.assertTrue(
            all(event["session_id"] == "test" for event in events)
        )

    def test_turn_and_subscribers_receive_flushed_phase_event_in_order(self):
        logger = Logger(dir=self.temp_dir.name, session_id="observed")
        received = []

        def first(event):
            on_disk = logger.path.read_text(encoding="utf-8").splitlines()
            received.append(("first", event, len(on_disk)))

        logger.subscribe(first)
        logger.subscribe(
            lambda event: received.append(("second", event, None))
        )
        logger.turn(n=3)
        events = self.events(logger)

        self.assertEqual([event["phase"] for event in events], ["session_start", "turn"])
        self.assertEqual(
            [name for name, _, _ in received],
            ["first", "second"],
        )
        self.assertEqual(received[0][1], {"phase": "turn", "n": 3})
        self.assertNotIn("session_id", received[0][1])
        self.assertEqual(received[0][2], 2)

    def test_subscribe_rejects_non_callable(self):
        logger = Logger(dir=self.temp_dir.name, session_id="invalid")
        with self.assertRaisesRegex(TypeError, "subscriber must be callable"):
            logger.subscribe("not callable")
        logger.close()

    def test_agent_logs_tool_failure_then_completion(self):
        logger = Logger(dir=self.temp_dir.name, session_id="agent")
        context = Context(task=PLAYER)
        context.add_message("user", "go")
        client = FakeClient(
            [
                response(
                    "tool_use",
                    [
                        {
                            "type": "tool_use",
                            "id": "call-1",
                            "name": "bad",
                            "input": {},
                        }
                    ],
                    usage={"input_tokens": 10, "output_tokens": 2},
                ),
                response(
                    "end_turn",
                    [{"type": "text", "text": "done"}],
                    usageMetadata={
                        "promptTokenCount": 20,
                        "candidatesTokenCount": 3,
                    },
                ),
            ]
        )
        agent = Agent(
            context=context,
            registry=FailingRegistry(),
            builder=FakeBuilder(),
            client=client,
            logger=logger,
        )

        self.assertEqual(agent.run(), "done")
        events = self.events(logger)

        self.assertEqual(
            [event["phase"] for event in events],
            [
                "session_start",
                "iteration",
                "prompt",
                "response",
                "tool_call",
                "tool_result",
                "iteration",
                "prompt",
                "response",
                "turn_end",
            ],
        )
        self.assertEqual(events[3]["text"], "(tool use — 1 call)")
        self.assertFalse(events[5]["ok"])
        self.assertEqual(
            events[5]["result"],
            "ERROR: ValueError: broken",
        )
        self.assertEqual(context.messages[-1].content, "ERROR: ValueError: broken")
        self.assertEqual(events[8]["input_tokens"], 20)
        self.assertEqual(events[8]["output_tokens"], 3)

    def test_iteration_limit_logs_one_tools_disabled_wrap_up(self):
        logger = Logger(dir=self.temp_dir.name, session_id="limit")
        context = Context(task=PLAYER)
        context.add_message("user", "go")
        client = FakeClient(
            [
                response(
                    "end_turn",
                    [{"type": "text", "text": "wrapped"}],
                )
            ]
        )
        agent = Agent(
            context=context,
            registry=FailingRegistry(),
            builder=FakeBuilder(),
            client=client,
            logger=logger,
            max_iterations=1,
        )
        agent.iteration = 1

        self.assertEqual(agent.run(), "wrapped")
        events = self.events(logger)

        self.assertEqual(
            [event["phase"] for event in events],
            ["session_start", "limit_reached", "response", "turn_end"],
        )
        self.assertEqual(
            client.calls,
            [{"tools": [], "max_output_tokens": 400}],
        )


if __name__ == "__main__":
    unittest.main()
