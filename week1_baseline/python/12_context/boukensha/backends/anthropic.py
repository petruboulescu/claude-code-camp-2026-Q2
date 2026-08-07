from .base import Backend


class Anthropic(Backend):
    BASE_URL = "https://api.anthropic.com/v1/messages"
    MODELS = {
        "claude-haiku-4-5": {
            "context_window": 200_000,
            "cost_per_million": {"input": 1.0, "output": 5.0},
            "usage_unit": "tokens",
        },
        "claude-haiku-4-5-20251001": {
            "context_window": 200_000,
            "cost_per_million": {"input": 1.0, "output": 5.0},
            "usage_unit": "tokens",
        },
        "claude-sonnet-4-6": {
            "context_window": 1_000_000,
            "cost_per_million": {"input": 3.0, "output": 15.0},
            "usage_unit": "tokens",
        },
        "claude-opus-4-8": {
            "context_window": 1_000_000,
            "cost_per_million": {"input": 5.0, "output": 25.0},
            "usage_unit": "tokens",
        },
    }

    def __init__(self, *, api_key, model):
        self.api_key = api_key
        self._configure_model(model)

    def to_messages(self, context):
        messages = []
        for message in context.messages:
            if message.role == "tool_result":
                messages.append(
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": message.tool_use_id,
                                "content": message.content,
                            }
                        ],
                    }
                )
            elif message.role == "assistant":
                messages.append({"role": "assistant", "content": self._assistant_content(message.content)})
            else:
                messages.append({"role": message.role, "content": message.content})
        return messages

    def to_tools(self, tools):
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": list(tool.parameters),
                },
            }
            for tool in tools.values()
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "model": self.model,
            "system": context.system,
            "max_tokens": max_output_tokens,
            "tools": self.to_tools(context.tools) if tools is None else tools,
            "messages": self.to_messages(context),
        }

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }

    @property
    def url(self):
        return self.BASE_URL

    def parse_response(self, response):
        stop_reason = (
            "tool_use"
            if response.get("stop_reason") == "tool_use"
            else "end_turn"
        )
        return {
            "stop_reason": stop_reason,
            "content": [self._normalize_block(block) for block in response.get("content") or []],
        }

    @staticmethod
    def _normalize_block(block):
        if block.get("type") == "thinking":
            return {"type": "reasoning", "text": str(block.get("thinking") or ""),
                    "signature": block.get("signature")}
        if block.get("type") == "redacted_thinking":
            return {"type": "reasoning", "text": "", "redacted": True,
                    "signature": block.get("data")}
        return block

    @staticmethod
    def _assistant_content(content):
        if isinstance(content, str):
            return content
        result = []
        for block in content:
            if block.get("type") != "reasoning":
                result.append(block)
            elif block.get("redacted"):
                result.append({"type": "redacted_thinking", "data": block.get("signature")})
            else:
                result.append({"type": "thinking", "thinking": str(block.get("text") or ""),
                               "signature": block.get("signature")})
        return result
