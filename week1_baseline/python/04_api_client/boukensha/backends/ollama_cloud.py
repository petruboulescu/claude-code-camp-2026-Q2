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

    def to_payload(self, context, max_output_tokens=1024):
        return {
            "model": self.model,
            "stream": False,
            "messages": self.to_messages(context),
            "tools": self.to_tools(context.tools),
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
