from .base import Backend


class OllamaCloud(Backend):
    BASE_URL = "https://ollama.com"
    MODELS = {
        "gemma4:31b-cloud": {
            "context_window": 256_000,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "ollama_cloud_usage",
            "usage_level": "medium",
        },
        "minimax-m3:cloud": {
            "context_window": 512_000,
            "advertised_context_window": 1_000_000,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "ollama_cloud_usage",
            "usage_level": "high",
        },
        "kimi-k2.5:cloud": {
            "context_window": 256_000,
            "cost_per_million": {"input": None, "output": None},
            "usage_unit": "ollama_cloud_usage",
            "usage_level": "high",
        },
    }

    def __init__(self, *, api_key, model):
        self.api_key = api_key
        self._configure_model(model)

    def to_messages(self, context):
        messages = [{"role": "system", "content": context.system}]
        for message in context.messages:
            if message.role == "tool_result":
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": message.tool_use_id,
                        "content": message.content,
                    }
                )
            elif message.role == "assistant":
                messages.append(self._assistant_message(message.content))
            else:
                messages.append({"role": message.role, "content": message.content})
        return messages

    def to_tools(self, tools):
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": tool.parameters,
                        "required": list(tool.parameters),
                    },
                },
            }
            for tool in tools.values()
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "model": self.model,
            "stream": False,
            "messages": self.to_messages(context),
            "tools": self.to_tools(context.tools) if tools is None else tools,
        }

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    @property
    def url(self):
        return f"{self.BASE_URL}/api/chat"

    def parse_response(self, response):
        message = response.get("message") or {}
        tool_calls = message.get("tool_calls") or []

        content = []
        if message.get("content"):
            content.append({"type": "text", "text": message["content"]})

        for tool_call in tool_calls:
            function = tool_call.get("function") or {}
            name = function.get("name")
            content.append(
                {
                    "type": "tool_use",
                    "id": name,
                    "name": name,
                    "input": function.get("arguments") or {},
                }
            )

        return {
            "stop_reason": "tool_use" if tool_calls else "end_turn",
            "content": content,
        }

    @staticmethod
    def _assistant_message(content):
        blocks = (
            [{"type": "text", "text": content}]
            if isinstance(content, str)
            else content
        )
        text_blocks = [block for block in blocks if block.get("type") == "text"]
        tool_blocks = [
            block for block in blocks if block.get("type") == "tool_use"
        ]

        message = {
            "role": "assistant",
            "content": "".join(block.get("text", "") for block in text_blocks),
        }
        if tool_blocks:
            message["tool_calls"] = [
                {
                    "function": {
                        "name": block.get("name"),
                        "arguments": block.get("input"),
                    }
                }
                for block in tool_blocks
            ]
        return message
