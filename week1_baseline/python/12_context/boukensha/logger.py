import json
import re
import secrets
from datetime import datetime, timezone
from pathlib import Path


class Logger:
    """Write one agent session as flush-on-write JSON Lines events."""

    DEFAULT_SESSION_DIR = "sessions"

    def __init__(
        self,
        *,
        session_id=None,
        dir=None,
        log=None,
        snapshot=None,
    ):
        self.session_id = session_id or self._generate_session_id()
        self.path = Path(log) if log is not None else Path(
            dir if dir is not None else self._default_dir()
        ) / f"{self.session_id}.jsonl"

        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._log_io = self.path.open("a", encoding="utf-8")
        self._subscribers = []
        self._write_log({"phase": "session_start", **(snapshot or {})})

    def turn(self, *, n):
        self._write_log({"phase": "turn", "n": n})

    def iteration(self, *, n, max):
        self._write_log({"phase": "iteration", "n": n, "max": max})

    def limit_reached(self, *, kind, n, max):
        self._write_log(
            {
                "phase": "limit_reached",
                "kind": kind,
                "n": n,
                "max": max,
            }
        )

    def turn_end(self, *, reason, iterations, tokens=None):
        self._write_log(
            {
                "phase": "turn_end",
                "reason": reason,
                "iterations": iterations,
                "tokens": tokens,
            }
        )

    def prompt(self, *, messages, tools, context_window=None):
        self._write_log(
            {
                "phase": "prompt",
                "message_count": len(messages),
                "messages": [
                    {"role": message.role, "content": message.content}
                    for message in messages
                ],
                "tool_count": len(tools),
                "tools": list(tools),
                "context_window": context_window,
            }
        )

    def compaction(self, *, before, dropped, context_window):
        self._write_log({"phase": "compaction", "before": before,
                         "dropped": dropped, "context_window": context_window})

    def reasoning(self, *, text, redacted=False):
        self._write_log({"phase": "reasoning", "text": str(text),
                         "redacted": redacted})

    def plan(self, *, text):
        self._write_log({"phase": "plan", "text": str(text).strip()})

    def usage_tokens(self, usage):
        tokens = self._usage_tokens(usage)
        return {key: value or 0 for key, value in tokens.items()}

    def tool_call(self, *, name, args):
        self._write_log(
            {"phase": "tool_call", "name": name, "args": args}
        )

    def tool_result(self, *, name, result, ok=True, error=None):
        self._write_log(
            {
                "phase": "tool_result",
                "name": name,
                "result": str(result),
                "ok": ok,
                "error": error,
            }
        )

    def response(
        self,
        *,
        text,
        usage=None,
        stop_reason=None,
        task=None,
        backend=None,
    ):
        event = {
            "phase": "response",
            "text": str(text).strip(),
            "usage": usage,
            "stop_reason": stop_reason,
        }
        event.update(
            self._execution_metadata(
                task=task,
                backend=backend,
                usage=usage,
            )
        )
        self._write_log(event)

    def raw(self, *, data):
        import boukensha

        if boukensha.is_debug():
            self._write_log({"phase": "raw", "data": data})

    def subscribe(self, callback):
        if not callable(callback):
            raise TypeError("subscriber must be callable")
        self._subscribers.append(callback)
        return callback

    def close(self):
        if self._log_io and not self._log_io.closed:
            self._log_io.close()

    def _default_dir(self):
        import boukensha

        return Path(boukensha.config().dir) / self.DEFAULT_SESSION_DIR

    def _write_log(self, event):
        phase_event = dict(event)
        event = {
            **event,
            "session_id": self.session_id,
            "at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
        self._log_io.write(
            json.dumps(event, separators=(",", ":"), ensure_ascii=False)
            + "\n"
        )
        self._log_io.flush()
        for subscriber in tuple(self._subscribers):
            subscriber(dict(phase_event))

    @staticmethod
    def _generate_session_id():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{timestamp}-{secrets.token_hex(4)}"

    def _execution_metadata(self, *, task, backend, usage):
        if not (task or backend or usage):
            return {}

        tokens = self._usage_tokens(usage)
        metadata = {
            "task": self._task_name(task),
            "provider": self._provider_name(backend),
            "model": getattr(backend, "model", None),
            "usage_unit": getattr(backend, "usage_unit", None),
            "usage_level": getattr(backend, "usage_level", None),
            "input_tokens": tokens["input"],
            "output_tokens": tokens["output"],
            "cost_usd": self._estimate_cost(backend, tokens),
        }
        return {
            key: value
            for key, value in metadata.items()
            if value is not None
        }

    @staticmethod
    def _task_name(task):
        if task is None:
            return None
        return getattr(task, "name", str(task))

    @staticmethod
    def _provider_name(backend):
        if backend is None:
            return None
        name = backend.__class__.__name__
        return re.sub(r"([a-z\d])([A-Z])", r"\1_\2", name).lower()

    def _usage_tokens(self, usage):
        usage = usage or {}
        return {
            "input": self._first_integer(
                usage,
                "input_tokens",
                "prompt_tokens",
                "promptTokenCount",
                "prompt_eval_count",
            ),
            "output": self._first_integer(
                usage,
                "output_tokens",
                "completion_tokens",
                "candidatesTokenCount",
                "eval_count",
            ),
        }

    @staticmethod
    def _first_integer(data, *keys):
        for key in keys:
            value = data.get(key)
            if value is not None:
                try:
                    return int(value)
                except (TypeError, ValueError):
                    return None
        return None

    @staticmethod
    def _estimate_cost(backend, tokens):
        if backend is None or not hasattr(backend, "estimate_cost"):
            return None
        if tokens["input"] is None or tokens["output"] is None:
            return None
        return backend.estimate_cost(
            input_tokens=tokens["input"],
            output_tokens=tokens["output"],
        )
