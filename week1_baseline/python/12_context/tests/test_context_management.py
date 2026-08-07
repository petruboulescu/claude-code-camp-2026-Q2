import tempfile
import unittest

from boukensha.agent import Agent
from boukensha.backends import Anthropic, Gemini, Ollama, OpenAI
from boukensha.context import Context
from boukensha.logger import Logger
from boukensha.models import Models


class StubBuilder:
    backend = None

    @staticmethod
    def parse_response(response):
        return response["parsed"]


class StubClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def call(self, **options):
        self.calls.append(options)
        return self.responses.pop(0)


class StubRegistry:
    def dispatch(self, name, args):
        return "ok"


class ContextTest(unittest.TestCase):
    def test_model_lookup_and_context_math(self):
        self.assertEqual(Models.context_window("claude-haiku-4-5"), 200_000)
        self.assertEqual(Models.context_window("unknown"), 32_000)
        context = Context(system="s", context_window=100, compaction_threshold=.85)
        context.update_tokens("85")
        context.add_turn_tokens("10", None)
        self.assertEqual(context.usage_pct, 85)
        self.assertTrue(context.needs_compaction())
        self.assertEqual(context.turn_tokens, 10)

    def test_compaction_drops_oldest_and_keeps_two(self):
        context = Context(system="s")
        for number in range(5):
            context.add_message("user", str(number))
        context.current_tokens = 99
        self.assertEqual(context.compact_messages(), 2)
        self.assertEqual([m.content for m in context.messages], ["2", "3", "4"])
        self.assertEqual(context.current_tokens, 0)
        self.assertEqual(context.compact_messages(), 1)
        self.assertEqual(len(context.messages), 2)

    def test_agent_compacts_accounts_and_stops_on_tokens(self):
        context = Context(system="s", context_window=100)
        for number in range(5):
            context.add_message("user", str(number))
        context.current_tokens = 90
        responses = [
            {"usage": {"input_tokens": 50, "output_tokens": 10},
             "parsed": {"stop_reason": "tool_use", "content": [
                 {"type": "reasoning", "text": "think"},
                 {"type": "text", "text": "plan"},
                 {"type": "tool_use", "id": "1", "name": "x", "input": {}},
             ]}},
            {"usage": {"input_tokens": 30, "output_tokens": 5},
             "parsed": {"stop_reason": "end_turn", "content": [
                 {"type": "text", "text": "summary"}
             ]}},
        ]
        with tempfile.TemporaryDirectory() as directory:
            logger = Logger(dir=directory)
            events = []
            logger.subscribe(events.append)
            agent = Agent(context=context, registry=StubRegistry(), builder=StubBuilder(),
                          client=StubClient(responses), logger=logger,
                          max_iterations=10, max_turn_tokens=60)
            self.assertEqual(agent.run(), "summary")
            logger.close()
        self.assertEqual(context.turn_tokens, 95)
        self.assertEqual(context.current_tokens, 30)
        self.assertEqual(events[0]["phase"], "compaction")
        self.assertTrue(any(e["phase"] == "reasoning" for e in events))
        self.assertTrue(any(e["phase"] == "plan" for e in events))
        self.assertTrue(any(e.get("kind") == "max_tokens" for e in events))
        self.assertEqual(events[-1]["tokens"], 95)


class BackendNormalizationTest(unittest.TestCase):
    def test_anthropic_reasoning_round_trip(self):
        backend = Anthropic(api_key="k", model="claude-haiku-4-5")
        parsed = backend.parse_response({"content": [
            {"type": "thinking", "thinking": "why", "signature": "sig"},
            {"type": "redacted_thinking", "data": "secret"},
        ]})
        self.assertEqual(parsed["content"][0]["type"], "reasoning")
        self.assertTrue(parsed["content"][1]["redacted"])
        self.assertEqual(backend._assistant_content(parsed["content"])[0]["signature"], "sig")

    def test_openai_responses_shapes(self):
        backend = OpenAI(api_key="k", model="gpt-5.4-mini")
        context = Context(system="system")
        context.add_message("assistant", [{"type": "tool_use", "id": "c1",
                                            "name": "look", "input": {"x": 1}}])
        context.add_message("tool_result", "done", tool_use_id="c1")
        payload = backend.to_payload(context)
        self.assertEqual(backend.url, "https://api.openai.com/v1/responses")
        self.assertEqual(payload["instructions"], "system")
        self.assertEqual(payload["input"][-1]["type"], "function_call_output")
        parsed = backend.parse_response({"output": [
            {"type": "reasoning", "summary": [{"text": "why"}]},
            {"type": "function_call", "call_id": "c2", "name": "go",
             "arguments": "{\"n\":2}"},
        ]})
        self.assertEqual(parsed["stop_reason"], "tool_use")
        self.assertEqual(parsed["content"][1]["input"], {"n": 2})

    def test_gemini_and_ollama_thinking(self):
        gemini = Gemini(api_key="k", model="gemini-2.5-flash")
        parsed = gemini.parse_response({"candidates": [{"content": {"parts": [
            {"thought": True, "text": "why", "thoughtSignature": "sig"}
        ]}}]})
        self.assertEqual(parsed["content"][0]["signature"], "sig")
        self.assertEqual(gemini.to_payload(Context(system="s"))["generationConfig"]
                         ["thinkingConfig"], {"thinkingBudget": 0})
        ollama = Ollama(model="gemma4")
        self.assertFalse(ollama.to_payload(Context(system="s"))["think"])
        self.assertEqual(ollama.parse_response({"message": {"thinking": "why"}})
                         ["content"][0]["type"], "reasoning")


if __name__ == "__main__":
    unittest.main()
