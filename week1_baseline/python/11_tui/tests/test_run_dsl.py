import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boukensha
from boukensha import Context, Registry, RunDSL
from boukensha.run_dsl import _build_backend


class RunDSLTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.old_config = boukensha._config
        boukensha._config = None

    def tearDown(self):
        boukensha._config = self.old_config
        self.temp_dir.cleanup()

    def test_tool_supports_decorator_and_direct_registration(self):
        context = Context()
        dsl = RunDSL(Registry(context))

        @dsl.tool(
            "decorated",
            description="decorated tool",
            parameters={"value": {"type": "integer"}},
        )
        def decorated(value):
            return value + 1

        def direct(value):
            return value * 2

        returned = dsl.tool(
            "direct",
            description="direct tool",
            func=direct,
        )

        self.assertIs(returned, direct)
        self.assertEqual(decorated(2), 3)
        self.assertEqual(context.tools["decorated"].func(value=2), 3)
        self.assertEqual(context.tools["direct"].func(value=3), 6)

    def test_tool_rejects_non_callable(self):
        context = Context()
        dsl = RunDSL(Registry(context))
        with self.assertRaisesRegex(TypeError, "tool function must be callable"):
            dsl.tool("bad", description="bad", func=3)

    def test_build_backend_supports_every_provider(self):
        cases = {
            "anthropic": "Anthropic",
            "openai": "OpenAI",
            "gemini": "Gemini",
            "ollama": "Ollama",
            "ollama_cloud": "OllamaCloud",
        }
        models = {
            "anthropic": "claude-haiku-4-5",
            "openai": "gpt-5.4-mini",
            "gemini": "gemini-2.5-flash",
            "ollama": "gemma4",
            "ollama_cloud": "gemma4:31b-cloud",
        }

        for provider, class_name in cases.items():
            with self.subTest(provider=provider):
                result = _build_backend(
                    provider=provider,
                    api_key="key",
                    model=models[provider],
                    ollama_host="http://ollama.example/",
                )
                self.assertEqual(result.__class__.__name__, class_name)
                self.assertEqual(result.model, models[provider])
                if provider == "ollama":
                    self.assertEqual(result.host, "http://ollama.example")
                else:
                    self.assertEqual(result.api_key, "key")

    def test_build_backend_rejects_unknown_provider(self):
        with self.assertRaisesRegex(
            ValueError,
            "Unknown backend 'unknown'.*anthropic.*ollama_cloud",
        ):
            _build_backend(
                provider="unknown",
                api_key=None,
                model="anything",
                ollama_host="http://localhost:11434",
            )

    def test_run_configures_tools_logs_snapshot_and_closes_logger(self):
        config_dir = Path(self.temp_dir.name) / "config"
        config_dir.mkdir()
        log_path = Path(self.temp_dir.name) / "run.jsonl"

        class FakeConfig:
            user_prompts_dir = str(config_dir / "prompts")

            @staticmethod
            def tasks(name):
                self.assertEqual(name, "player")
                return {
                    "max_iterations": 4,
                    "max_output_tokens": 99,
                }

        captured = {}

        def configure(dsl):
            @dsl.tool(
                "echo",
                description="Echo text",
                parameters={"text": {"type": "string"}},
            )
            def echo(text):
                return text

        def fake_call(client, max_output_tokens=1024, tools=None):
            captured["context"] = client.builder.context
            captured["max_output_tokens"] = max_output_tokens
            return {
                "message": {"content": "finished"},
                "done_reason": "stop",
                "prompt_eval_count": 3,
                "eval_count": 1,
            }

        with (
            patch.object(boukensha, "_config", FakeConfig()),
            patch("boukensha.client.Client.call", new=fake_call),
        ):
            result = boukensha.run(
                task="do it",
                system="system",
                model="gemma4",
                backend="ollama",
                log=log_path,
                max_output_tokens=77,
                configure=configure,
            )

        self.assertEqual(result, "finished")
        self.assertEqual(captured["max_output_tokens"], 77)
        self.assertEqual(captured["context"].messages[0].content, "do it")
        self.assertIn("echo", captured["context"].tools)
        events = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(events[0]["task"], "player")
        self.assertEqual(events[0]["max_iterations"], 4)
        self.assertEqual(events[0]["max_output_tokens"], 77)
        self.assertEqual(events[0]["provider"], "ollama")
        self.assertEqual(events[-1]["phase"], "turn_end")
        with log_path.open("a", encoding="utf-8") as stream:
            stream.write("")

    def test_run_closes_logger_when_agent_raises(self):
        log_path = Path(self.temp_dir.name) / "failed.jsonl"

        class TrackingLogger:
            instance = None

            def __init__(self, **kwargs):
                self.closed = False
                TrackingLogger.instance = self

            def close(self):
                self.closed = True

            def __getattr__(self, name):
                return lambda **kwargs: None

        class FakeConfig:
            user_prompts_dir = self.temp_dir.name

            @staticmethod
            def tasks(name):
                return {"max_iterations": 2, "max_output_tokens": 10}

        with (
            patch.object(boukensha, "_config", FakeConfig()),
            patch("boukensha.run_dsl.Logger", TrackingLogger),
            patch(
                "boukensha.run_dsl.Agent.run",
                side_effect=KeyboardInterrupt,
            ),
        ):
            with self.assertRaises(KeyboardInterrupt):
                boukensha.run(
                    task="stop",
                    system="system",
                    model="gemma4",
                    backend="ollama",
                    log=log_path,
                )

        self.assertTrue(TrackingLogger.instance.closed)

    def test_run_registers_mcp_before_configure_and_closes_client(self):
        class FakeMcpClient:
            tools = [{"name": "look"}]

            def __init__(self):
                self.closed = False

            def close(self):
                self.closed = True

        mcp_client = FakeMcpClient()

        class FakeConfig:
            dir = self.temp_dir.name
            user_prompts_dir = self.temp_dir.name
            mcp_servers = {
                "mud": {
                    "command": "fixture",
                    "args": [],
                    "env": {},
                    "prefix": None,
                    "required": True,
                }
            }

            @staticmethod
            def tasks(name):
                return {"max_iterations": 2, "max_output_tokens": 10}

        captured = {}

        def register_mcp(registry, **_entry):
            registry.tool("look", description="remote", func=lambda: "room")
            return mcp_client

        def configure(dsl):
            captured["names_before_configure"] = dsl.tool_names

        def agent_run(agent):
            captured["working_dir"] = agent.context.working_dir
            return "done"

        with (
            patch.object(boukensha, "_config", FakeConfig()),
            patch("boukensha.run_dsl.mcp_tools.register", side_effect=register_mcp),
            patch("boukensha.run_dsl.Agent.run", new=agent_run),
        ):
            result = boukensha.run(
                task="go",
                system="system",
                model="gemma4",
                backend="ollama",
                working_dir=".",
                configure=configure,
            )

        self.assertEqual(result, "done")
        self.assertEqual(captured["names_before_configure"], ("look",))
        self.assertTrue(Path(captured["working_dir"]).is_absolute())
        self.assertTrue(mcp_client.closed)

    def test_repl_configures_once_passes_effective_values_and_closes(self):
        class FakeConfig:
            dir = self.temp_dir.name
            user_prompts_dir = self.temp_dir.name

            @staticmethod
            def tasks(name):
                return {"max_iterations": 4, "max_output_tokens": 99}

        captured = {}

        class TrackingLogger:
            instance = None

            def __init__(self, **kwargs):
                self.closed = False
                self.kwargs = kwargs
                TrackingLogger.instance = self

            def close(self):
                self.closed = True

        class FakeRepl:
            def __init__(self, **kwargs):
                captured.update(kwargs)

            def start(self):
                return "done"

        configure_calls = []

        def configure(dsl):
            configure_calls.append(dsl)

            @dsl.tool("echo", description="Echo")
            def echo(value):
                return value

        with (
            patch.object(boukensha, "_config", FakeConfig()),
            patch("boukensha.run_dsl.Logger", TrackingLogger),
            patch("boukensha.run_dsl.Repl", FakeRepl),
        ):
            result = boukensha.repl(
                system="system",
                model="gemma4",
                backend="ollama",
                max_output_tokens=77,
                configure=configure,
                tui=False,
            )

        self.assertEqual(result, "done")
        self.assertEqual(len(configure_calls), 1)
        self.assertIn("echo", captured["context"].tools)
        self.assertEqual(captured["max_iterations"], 4)
        self.assertEqual(captured["max_output_tokens"], 77)
        self.assertEqual(captured["version"], "0.11.1")
        self.assertEqual(captured["servers"], {})
        self.assertTrue(TrackingLogger.instance.closed)

    def test_repl_closes_logger_after_keyboard_interrupt(self):
        class FakeConfig:
            dir = self.temp_dir.name
            user_prompts_dir = self.temp_dir.name

            @staticmethod
            def tasks(name):
                return {"max_iterations": 2, "max_output_tokens": 10}

        class TrackingLogger:
            instance = None

            def __init__(self, **kwargs):
                self.closed = False
                TrackingLogger.instance = self

            def close(self):
                self.closed = True

        class InterruptingRepl:
            def __init__(self, **kwargs):
                pass

            def start(self):
                raise KeyboardInterrupt

        with (
            patch.object(boukensha, "_config", FakeConfig()),
            patch("boukensha.run_dsl.Logger", TrackingLogger),
            patch("boukensha.run_dsl.Repl", InterruptingRepl),
            patch("builtins.print"),
        ):
            result = boukensha.repl(
                system="system",
                model="gemma4",
                backend="ollama",
                tui=False,
            )

        self.assertIsNone(result)
        self.assertTrue(TrackingLogger.instance.closed)


if __name__ == "__main__":
    unittest.main()
