from .base import Backend


class Gemini(Backend):
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
    MODELS = {
        "gemini-3.5-flash": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 1.5, "output": 9.0},
            "usage_unit": "tokens",
        },
        "gemini-3.1-flash-lite": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 0.25, "output": 1.5},
            "usage_unit": "tokens",
        },
        "gemini-2.5-pro": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 1.25, "output": 10.0},
            "usage_unit": "tokens",
        },
        "gemini-2.5-flash": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 0.30, "output": 2.50},
            "usage_unit": "tokens",
        },
        "gemini-2.5-flash-lite": {
            "context_window": 1_048_576,
            "cost_per_million": {"input": 0.10, "output": 0.40},
            "usage_unit": "tokens",
        },
    }

    def __init__(self, *, api_key, model):
        self.api_key = api_key
        self._configure_model(model)

    def to_messages(self, context):
        messages = []
        for message in context.messages:
            if message.role == "assistant":
                messages.append(
                    {"role": "model", "parts": self._assistant_parts(message.content)}
                )
            elif message.role == "tool_result":
                messages.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": message.tool_use_id,
                                    "response": {"content": message.content},
                                }
                            }
                        ],
                    }
                )
            else:
                messages.append(
                    {"role": message.role, "parts": [{"text": message.content}]}
                )
        return messages

    def to_tools(self, tools):
        if not tools:
            return []

        return [
            {
                "functionDeclarations": [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": {
                            "type": "object",
                            "properties": tool.parameters,
                            "required": list(tool.parameters),
                        },
                    }
                    for tool in tools.values()
                ]
            }
        ]

    def to_payload(self, context, max_output_tokens=1024, tools=None):
        return {
            "systemInstruction": {"parts": [{"text": context.system}]},
            "contents": self.to_messages(context),
            "tools": self.to_tools(context.tools) if tools is None else tools,
            "generationConfig": {"maxOutputTokens": max_output_tokens,
                                 "thinkingConfig": self._thinking_config()},
        }

    @property
    def headers(self):
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }

    @property
    def url(self):
        return f"{self.BASE_URL}/{self.model}:generateContent"

    def parse_response(self, response):
        candidates = response.get("candidates") or []
        candidate_content = (
            (candidates[0].get("content") or {}) if candidates else {}
        )
        parts = candidate_content.get("parts") or []

        content = []
        tool_used = False

        for part in parts:
            function_call = part.get("functionCall")
            if function_call:
                name = function_call.get("name")
                content.append(
                    {
                        "type": "tool_use",
                        "id": name,
                        "name": name,
                        "input": function_call.get("args") or {},
                        "signature": part.get("thoughtSignature"),
                    }
                )
                tool_used = True
            elif part.get("thought"):
                content.append({"type": "reasoning", "text": str(part.get("text") or ""),
                                "signature": part.get("thoughtSignature")})
            elif part.get("text") is not None:
                content.append({"type": "text", "text": part["text"]})

        return {
            "stop_reason": "tool_use" if tool_used else "end_turn",
            "content": content,
        }

    @staticmethod
    def _assistant_parts(content):
        blocks = (
            [{"type": "text", "text": content}]
            if isinstance(content, str)
            else content
        )
        parts = []
        for block in blocks:
            if block.get("type") == "tool_use":
                part = {
                        "functionCall": {
                            "name": block.get("name"),
                            "args": block.get("input"),
                        }}
                if block.get("signature"):
                    part["thoughtSignature"] = block["signature"]
                parts.append(part)
            elif block.get("type") == "reasoning":
                part = {"text": str(block.get("text") or ""), "thought": True}
                if block.get("signature"):
                    part["thoughtSignature"] = block["signature"]
                parts.append(part)
            else:
                parts.append({"text": block.get("text")})
        return parts

    def _thinking_config(self):
        if self.model == "gemini-3.1-pro-preview-customtools":
            return {"thinkingLevel": "LOW"}
        return {"thinkingBudget": 0}
