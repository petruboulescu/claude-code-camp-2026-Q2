import math
import os

from .message import Message


class Context:
    def __init__(self, task=None, system=None, context_window=200_000,
                 working_dir=None, compaction_threshold=0.85):
        self.task = task
        self.system = system
        self.context_window = int(context_window)
        self.compaction_threshold = float(compaction_threshold)
        self.working_dir = (
            os.path.abspath(os.path.expanduser(os.fspath(working_dir)))
            if working_dir is not None
            else None
        )
        self.messages = []
        self.tools = {}
        self.current_tokens = 0
        self.turn_tokens = 0

    def register_tool(self, tool):
        self.tools[tool.name] = tool

    def add_message(self, role, content, tool_use_id=None):
        self.messages.append(Message(role=role, content=content, tool_use_id=tool_use_id))

    def clear_messages(self):
        """Clear conversation history while retaining system state and tools."""
        self.messages.clear()
        self.current_tokens = 0

    def update_tokens(self, value):
        self.current_tokens = self._integer(value)

    def reset_turn_tokens(self):
        self.turn_tokens = 0

    def add_turn_tokens(self, input_tokens, output_tokens):
        self.turn_tokens += self._integer(input_tokens) + self._integer(output_tokens)

    @property
    def usage_fraction(self):
        return self.current_tokens / self.context_window if self.context_window > 0 else 0.0

    @property
    def usage_pct(self):
        return round(self.usage_fraction * 100)

    def needs_compaction(self, threshold=None):
        threshold = self.compaction_threshold if threshold is None else threshold
        return self.usage_fraction >= float(threshold)

    def compact_messages(self, target_fraction=0.60):
        del target_fraction
        count = min(math.ceil(len(self.messages) * 0.40), len(self.messages) - 2)
        count = max(count, 0)
        del self.messages[:count]
        self.current_tokens = 0
        return count

    @staticmethod
    def _integer(value):
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @property
    def tool_count(self):
        return len(self.tools)

    @property
    def turn_count(self):
        return len(self.messages)

    def __str__(self):
        task_name = self.task.name if self.task else None
        return (f"<Context task={task_name} turns={self.turn_count} "
                f"tools={self.tool_count} window={self.context_window} "
                f"current={self.current_tokens}>")

    def __repr__(self):
        return str(self)
