from .errors import ApiError, TurnCancelled
from .logger import Logger


class Agent:
    """Run a bounded synchronous model/tool loop."""

    MAX_ITERATIONS = 25
    WRAP_UP_OUTPUT_TOKENS = 400
    WRAP_UP_DIRECTIVE = (
        "You have reached your action limit for this turn. "
        "Do not call any more tools.\n"
        "Briefly summarize what you accomplished, what is still unfinished, and the\n"
        "single next action you would take."
    )

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        logger=None,
        task_settings=None,
        max_iterations=None,
        max_turn_tokens=None,
        max_output_tokens=None,
        cancel_event=None,
    ):
        self.context = context
        self.registry = registry
        self.builder = builder
        self.client = client
        self.logger = logger if logger is not None else Logger()
        self.max_iterations = self._resolve_max_iterations(
            task_settings,
            max_iterations,
        )
        self.max_output_tokens = self._resolve_max_output_tokens(
            task_settings,
            max_output_tokens,
        )
        self.max_turn_tokens = int(max_turn_tokens or 0)
        self.iteration = 0
        self.cancel_event = cancel_event

    def run(self):
        self.context.reset_turn_tokens()
        self._compact_if_needed()
        while True:
            self._check_cancelled()
            if self._iteration_limit_reached():
                self.logger.limit_reached(
                    kind="max_iterations",
                    n=self.iteration,
                    max=self.max_iterations,
                )
                return self._wrap_up("max_iterations")
            if self._token_limit_reached():
                self.logger.limit_reached(kind="max_tokens", n=self.context.turn_tokens,
                                          max=self.max_turn_tokens)
                return self._wrap_up("max_tokens")

            self.iteration += 1
            self.logger.iteration(
                n=self.iteration,
                max=self.max_iterations,
            )
            self.logger.prompt(
                messages=self.context.messages,
                tools=self.context.tools,
                context_window=self.context.context_window,
            )

            self._check_cancelled()
            response = self.client.call(**self._call_options())
            self._check_cancelled()
            self.logger.raw(data=response)
            parsed = self.builder.parse_response(response)
            self._record_usage(response)
            self._log_reasoning(parsed["content"])

            if parsed["stop_reason"] == "tool_use":
                self._handle_tool_calls(parsed["content"], response)
            else:
                text = self._extract_text(parsed["content"])
                self.logger.response(text=text, usage=self._normalized_usage(response),
                                     stop_reason=parsed["stop_reason"], task=None,
                                     backend=self.builder.backend)
                self.logger.turn_end(
                    reason="completed",
                    iterations=self.iteration,
                    tokens=self.context.turn_tokens,
                )
                self.context.add_message("assistant", text)
                return text

    def _resolve_max_iterations(self, task_settings, explicit):
        if explicit is not None:
            return int(explicit)
        if (
            task_settings is not None
            and self.context.task is not None
            and hasattr(self.context.task, "max_iterations")
        ):
            return self.context.task.max_iterations(task_settings)
        return self.MAX_ITERATIONS

    def _resolve_max_output_tokens(self, task_settings, explicit):
        if explicit is not None:
            return explicit
        if (
            task_settings is not None
            and self.context.task is not None
            and hasattr(self.context.task, "max_output_tokens")
        ):
            return self.context.task.max_output_tokens(task_settings)
        return None

    def _iteration_limit_reached(self):
        return (
            self.max_iterations > 0
            and self.iteration >= self.max_iterations
        )

    def _token_limit_reached(self):
        return self.max_turn_tokens > 0 and self.context.turn_tokens >= self.max_turn_tokens

    def _record_usage(self, response):
        usage = self._normalized_usage(response) or {}
        tokens = {
            "input": self._usage_value(usage, "input_tokens", "prompt_tokens",
                                       "promptTokenCount", "prompt_eval_count"),
            "output": self._usage_value(usage, "output_tokens", "completion_tokens",
                                        "candidatesTokenCount", "eval_count"),
        }
        self.context.add_turn_tokens(tokens["input"], tokens["output"])
        self.context.update_tokens(tokens["input"])

    def _compact_if_needed(self):
        if not self.context.needs_compaction():
            return
        before = self.context.current_tokens
        dropped = self.context.compact_messages()
        self.logger.compaction(before=before, dropped=dropped,
                               context_window=self.context.context_window)

    @staticmethod
    def _usage_value(usage, *keys):
        for key in keys:
            try:
                if usage.get(key) is not None:
                    return int(usage[key])
            except (TypeError, ValueError):
                return 0
        return 0

    def _call_options(self):
        if self.max_output_tokens:
            return {"max_output_tokens": self.max_output_tokens}
        return {}

    def _wrap_up(self, reason):
        self._check_cancelled()
        self.context.add_message("user", self.WRAP_UP_DIRECTIVE)
        try:
            response = self.client.call(
                tools=[],
                max_output_tokens=self.WRAP_UP_OUTPUT_TOKENS,
            )
            self._check_cancelled()
            parsed = self.builder.parse_response(response)
            text = self._extract_text(parsed["content"])
            if not text.strip():
                text = self._fallback_message(reason)
            self._record_usage(response)
            self._log_response(text=text, response=response)
            self.logger.turn_end(
                reason=reason,
                iterations=self.iteration,
                tokens=self.context.turn_tokens,
            )
            self.context.add_message("assistant", text)
            return text
        except ApiError:
            message = self._fallback_message(reason)
            self.logger.turn_end(
                reason=reason,
                iterations=self.iteration,
                tokens=self.context.turn_tokens,
            )
            self.context.add_message("assistant", message)
            return message

    def _fallback_message(self, reason):
        return (
            f"I reached my {self.max_iterations}-action limit for this turn "
            f"before finishing ({reason}). Ask me to continue and I'll pick up "
            "from here."
        )

    @staticmethod
    def _extract_text(content):
        return "\n".join(
            block["text"]
            for block in content
            if block.get("type") == "text"
        )

    def _handle_tool_calls(self, content, response):
        tool_calls = [
            block
            for block in content
            if block.get("type") == "tool_use"
        ]
        preamble = self._extract_text(content)
        if preamble.strip():
            self.logger.plan(text=preamble)
        suffix = "" if len(tool_calls) == 1 else "s"
        placeholder = f"(tool use — {len(tool_calls)} call{suffix})"
        self._log_response(text=placeholder, response=response)

        self.context.add_message("assistant", content)

        for block in tool_calls:
            self._check_cancelled()
            name = block["name"]
            args = block["input"]
            tool_use_id = block["id"]

            self.logger.tool_call(name=name, args=args)
            try:
                result = self.registry.dispatch(name, args)
                self.logger.tool_result(
                    name=name,
                    result=result,
                    ok=True,
                )
            except Exception as error:
                result = (
                    f"ERROR: {error.__class__.__name__}: {error}"
                )
                self.logger.tool_result(
                    name=name,
                    result=result,
                    ok=False,
                    error=str(error),
                )

            self._check_cancelled()

            result_text = str(result)

            self.context.add_message(
                "tool_result",
                result_text,
                tool_use_id=tool_use_id,
            )

    def _check_cancelled(self):
        if self.cancel_event is not None and self.cancel_event.is_set():
            raise TurnCancelled("turn interrupted")

    def _log_reasoning(self, content):
        for block in content:
            if block.get("type") != "reasoning":
                continue
            text = str(block.get("text") or "")
            redacted = block.get("redacted") is True
            if text.strip() or redacted:
                self.logger.reasoning(text=text, redacted=redacted)

    def _log_response(self, *, text, response):
        self.logger.response(
            text=text,
            usage=self._normalized_usage(response),
            stop_reason=response.get("stop_reason"),
            task=self.context.task,
            backend=self.builder.backend,
        )

    @staticmethod
    def _normalized_usage(response):
        if response.get("usage") is not None:
            return response["usage"]
        if response.get("usageMetadata") is not None:
            return response["usageMetadata"]

        usage = {
            key: response[key]
            for key in ("prompt_eval_count", "eval_count")
            if key in response
        }
        return usage or None
