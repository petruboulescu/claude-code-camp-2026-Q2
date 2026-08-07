import json

from .base import Backend


class OpenAI(Backend):
    BASE_URL = "https://api.openai.com/v1/responses"
    MODELS = {
        "gpt-5.5": {"context_window": 1_000_000, "cost_per_million": {"input": 5.0, "output": 30.0}, "usage_unit": "tokens"},
        "gpt-5.4-mini": {"context_window": 400_000, "cost_per_million": {"input": 0.75, "output": 4.5}, "usage_unit": "tokens"},
        "gpt-5.4-nano": {"context_window": 400_000, "cost_per_million": {"input": 0.2, "output": 1.25}, "usage_unit": "tokens"},
    }

    def __init__(self, *, api_key, model):
        self.api_key = api_key
        self._configure_model(model)

    def to_input(self, context):
        items = []
        for message in context.messages:
            if message.role == "tool_result":
                items.append({"type": "function_call_output", "call_id": message.tool_use_id,
                              "output": str(message.content)})
            elif message.role == "assistant":
                items.extend(self._assistant_items(message.content))
            else:
                items.append({"role": message.role, "content": message.content})
        return items

    def to_tools(self, tools):
        return [{"type": "function", "name": tool.name, "description": tool.description,
                 "parameters": {"type": "object", "properties": tool.parameters,
                                "required": list(tool.parameters)}} for tool in tools.values()]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {"model": self.model, "instructions": context.system,
                "input": self.to_input(context),
                "tools": self.to_tools(context.tools) if tools is None else tools,
                "max_output_tokens": max_output_tokens, "reasoning": {"effort": "none"}}

    @property
    def headers(self):
        return {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

    @property
    def url(self):
        return self.BASE_URL

    def parse_response(self, response):
        content, calls = [], []
        for item in response.get("output") or []:
            if item.get("type") == "reasoning":
                text = "".join(part.get("text", "") for part in item.get("summary") or [])
                content.append({"type": "reasoning", "text": text})
            elif item.get("type") == "message":
                text = "".join(part.get("text", "") for part in item.get("content") or []
                               if part.get("type") == "output_text")
                if text:
                    content.append({"type": "text", "text": text})
            elif item.get("type") == "function_call":
                calls.append(item)
        for call in calls:
            content.append({"type": "tool_use", "id": call.get("call_id"), "name": call.get("name"),
                            "input": json.loads(call.get("arguments") or "{}")})
        return {"stop_reason": "tool_use" if calls else "end_turn", "content": content}

    @staticmethod
    def _assistant_items(content):
        blocks = [{"type": "text", "text": content}] if isinstance(content, str) else content
        text = "".join(block.get("text", "") for block in blocks if block.get("type") == "text")
        items = [{"role": "assistant", "content": text}] if text else []
        items.extend({"type": "function_call", "call_id": block.get("id"), "name": block.get("name"),
                      "arguments": json.dumps(block.get("input"))} for block in blocks
                     if block.get("type") == "tool_use")
        return items
