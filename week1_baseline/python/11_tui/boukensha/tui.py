"""Responsive Textual front end for a :class:`boukensha.repl.Repl`."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, replace
from datetime import datetime

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Input, RichLog, Static

from .errors import TurnCancelled
from .repl import CommandResult, Repl


def format_tokens(value) -> str:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        number = 0
    return f"{number / 1000:.1f}k" if number >= 1000 else str(number)


@dataclass(frozen=True)
class ProgressState:
    active: bool = False
    action: str = "idle"
    iteration: int = 0
    tool_calls: int = 0
    turn_input_tokens: int = 0
    turn_output_tokens: int = 0
    session_input_tokens: int = 0
    session_output_tokens: int = 0
    turns: int = 0
    started_at: float | None = None


def reduce_event(state: ProgressState, event: dict) -> ProgressState:
    phase = str(event.get("phase", ""))
    if phase == "iteration":
        return replace(state, iteration=_integer(event.get("n")), action="Thinking…")
    if phase == "tool_call":
        return replace(state, action=f"Calling tool: {event.get('name', '')}",
                       tool_calls=state.tool_calls + 1)
    if phase == "tool_result":
        return replace(state, action="Awaiting result…")
    if phase == "response":
        usage = event.get("usage") or {}
        input_tokens = _usage_value(usage, "input_tokens", "prompt_tokens",
                                   "promptTokenCount", "prompt_eval_count")
        output_tokens = _usage_value(usage, "output_tokens", "completion_tokens",
                                    "candidatesTokenCount", "eval_count")
        return replace(
            state,
            turn_input_tokens=state.turn_input_tokens + input_tokens,
            turn_output_tokens=state.turn_output_tokens + output_tokens,
            session_input_tokens=state.session_input_tokens + input_tokens,
            session_output_tokens=state.session_output_tokens + output_tokens,
        )
    return state


def _integer(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _usage_value(usage, *keys) -> int:
    if not isinstance(usage, dict):
        return 0
    for key in keys:
        if key in usage:
            return _integer(usage[key])
    return 0


class Tui(App):
    """Four-zone terminal application around an existing REPL session."""

    CSS = """
    Screen { layout: vertical; }
    #conversation { height: 1fr; padding: 0 1; }
    #progress { height: 1; color: cyan; padding: 0 1; }
    #input-row { height: 3; }
    #input { width: 1fr; border: none; }
    #status { height: 1; color: white; background: #444444; padding: 0 1; }
    """
    BINDINGS = [
        Binding("escape", "interrupt", "Interrupt", show=False),
        Binding("ctrl+l", "clear", "Clear", show=False),
        Binding("pageup", "page_up", "Page up", show=False),
        Binding("pagedown", "page_down", "Page down", show=False),
        Binding("ctrl+c", "request_quit", "Quit", show=False, priority=True),
        Binding("ctrl+d", "request_quit", "Quit", show=False, priority=True),
    ]

    class ReplOutput(Message):
        def __init__(self, text: str, turn_id: int):
            super().__init__()
            self.text, self.turn_id = text, turn_id

    class LogEvent(Message):
        def __init__(self, event: dict, turn_id: int):
            super().__init__()
            self.event, self.turn_id = event, turn_id

    class TurnFinished(Message):
        def __init__(self, turn_id: int, outcome: str, error: str | None = None):
            super().__init__()
            self.turn_id, self.outcome, self.error = turn_id, outcome, error

    def __init__(self, repl: Repl):
        super().__init__()
        self.repl = repl
        self.progress = ProgressState()
        self._turn_id = 0
        self._cancel_event: threading.Event | None = None
        self._quit_requested = False
        self._spinner_index = 0

    def compose(self) -> ComposeResult:
        yield RichLog(id="conversation", wrap=True, markup=False)
        yield Static(id="progress")
        with Vertical(id="input-row"):
            yield Input(placeholder="Type a message…", id="input")
        yield Static(id="status")

    def on_mount(self) -> None:
        self.query_one("#conversation", RichLog).write(self.repl.banner())
        self.repl.on_output(self._relay_output)
        self.repl.logger.subscribe(self._relay_event)
        self.set_interval(0.1, self._refresh_lines)
        self.query_one("#input", Input).focus()
        self._refresh_lines()

    def start(self):
        return self.run()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text or self.progress.active:
            return
        event.input.clear()
        result = self.repl.handle_command(text)
        if result is CommandResult.QUIT:
            self.exit()
        elif result is CommandResult.COMMAND:
            if text == "/clear":
                self.progress = replace(self.progress, turns=0)
                log = self.query_one("#conversation", RichLog)
                log.clear()
                log.write("(conversation history cleared)")
        else:
            self.query_one("#conversation", RichLog).write(f"> {text}")
            self._launch_turn(text)

    def _launch_turn(self, text: str) -> None:
        self._turn_id += 1
        turn_id = self._turn_id
        self._cancel_event = threading.Event()
        self.progress = replace(
            self.progress, active=True, action="Thinking…", iteration=0,
            tool_calls=0, turn_input_tokens=0, turn_output_tokens=0,
            started_at=time.monotonic(),
        )

        def work():
            outcome, error = "complete", None
            try:
                self.repl.run_turn(text, cancel_event=self._cancel_event)
            except TurnCancelled:
                outcome = "interrupted"
            except Exception as exc:  # keep UI alive; logger still owns details
                outcome, error = "error", str(exc)
            finally:
                self.post_message(self.TurnFinished(turn_id, outcome, error))

        self.run_worker(work, thread=True, name=f"turn-{turn_id}")

    def _relay_output(self, text: str) -> None:
        self.post_message(self.ReplOutput(str(text), self._turn_id))

    def _relay_event(self, event: dict) -> None:
        self.post_message(self.LogEvent(dict(event), self._turn_id))

    def on_tui_repl_output(self, message: ReplOutput) -> None:
        if message.turn_id == self._turn_id:
            self.query_one("#conversation", RichLog).write(message.text)

    def on_tui_log_event(self, message: LogEvent) -> None:
        if message.turn_id == self._turn_id:
            self.progress = reduce_event(self.progress, message.event)

    def on_tui_turn_finished(self, message: TurnFinished) -> None:
        if message.turn_id != self._turn_id:
            return
        if message.outcome == "interrupted":
            self.query_one("#conversation", RichLog).write("[interrupted]")
        elif message.outcome == "error":
            self.query_one("#conversation", RichLog).write(f"[error] {message.error}")
        self.progress = replace(self.progress, active=False, action="idle",
                                turns=self.progress.turns + 1)
        self._cancel_event = None
        if self._quit_requested:
            self.exit()

    def action_interrupt(self) -> None:
        if self._cancel_event is not None:
            self._cancel_event.set()

    def action_clear(self) -> None:
        if self.progress.active:
            return
        self.repl.handle_command("/clear")
        self.progress = replace(self.progress, turns=0)
        log = self.query_one("#conversation", RichLog)
        log.clear()
        log.write("(conversation history cleared)")

    def action_page_up(self) -> None:
        self.query_one("#conversation", RichLog).scroll_page_up(animate=False)

    def action_page_down(self) -> None:
        self.query_one("#conversation", RichLog).scroll_page_down(animate=False)

    def action_request_quit(self) -> None:
        if self._cancel_event is None:
            self.exit()
        else:
            self._quit_requested = True
            self._cancel_event.set()

    def _refresh_lines(self) -> None:
        frames = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        if self.progress.active:
            frame = frames[self._spinner_index % len(frames)]
            self._spinner_index += 1
            elapsed = int(time.monotonic() - (self.progress.started_at or time.monotonic()))
            maximum = self.repl.max_iterations or 25
            line = (f"{frame} {self.progress.action}  (iter {self.progress.iteration}/{maximum} · "
                    f"{elapsed}s · ↑ {format_tokens(self.progress.turn_input_tokens)} · "
                    f"↓ {format_tokens(self.progress.turn_output_tokens)} · "
                    f"{self.progress.tool_calls} calls)")
        else:
            line = f"  [ready]   ctx {format_tokens(self.progress.session_input_tokens)}   {self.progress.turns} turns"
        self.query_one("#progress", Static).update(line)
        model = self.repl.model or "(model)"
        status = (f" boukensha v{self.repl.version or '?.?.?'} · {model} · "
                  f"ctx {format_tokens(self.progress.session_input_tokens)} · "
                  f"{self.repl.context.tool_count} tools · {datetime.now().strftime('%H:%M:%S')} ")
        self.query_one("#status", Static).update(status)
