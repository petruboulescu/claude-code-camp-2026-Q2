"""Register tools discovered from an arbitrary MCP server."""

from __future__ import annotations

from ..mcp import Client


SEPARATOR = "__"


class CollisionError(ValueError):
    """Raised when two tools would have the same local name."""


def register(registry, *, command, args=None, env=None, prefix=None):
    client = Client.spawn(command=command, args=args or [], env=env or {})
    try:
        register_client(registry, client, prefix=prefix)
    except Exception:
        client.close()
        raise
    return client


def register_client(registry, client, *, prefix=None):
    taken = set(registry.tool_names)
    for definition in client.tools:
        remote_name = str(definition.get("name", ""))
        local_name = prefixed(remote_name, prefix)
        if local_name in taken:
            raise CollisionError(
                f"boukensha: MCP tool name collision on {local_name!r} — a tool "
                "by that name is already registered. Give this server a "
                "distinct `prefix` in mcp_servers."
            )
        taken.add(local_name)

        def invoke(_client=client, _remote_name=remote_name, **kwargs):
            result = _client.call_tool(
                _remote_name,
                {str(key): value for key, value in kwargs.items()},
            )
            return f"error: {result['text']}" if result["error"] else result["text"]

        registry.tool(
            local_name,
            description=str(definition.get("description") or ""),
            parameters=to_boukensha_params(definition.get("inputSchema")),
            func=invoke,
        )
    return len(client.tools)


def prefixed(name, prefix):
    normalized = "" if prefix is None else str(prefix).strip()
    return str(name) if not normalized else f"{normalized}{SEPARATOR}{name}"


def to_boukensha_params(input_schema):
    if not isinstance(input_schema, dict):
        return {}
    properties = input_schema.get("properties") or {}
    if not isinstance(properties, dict):
        return {}
    parameters = {}
    for name, raw_schema in properties.items():
        schema = raw_schema if isinstance(raw_schema, dict) else {}
        description = str(schema.get("description") or "")
        choices = schema.get("enum")
        if isinstance(choices, list):
            enum_text = f"(one of: {', '.join(str(value) for value in choices)})"
            description = f"{description} {enum_text}".strip()
        parameters[str(name)] = {
            "type": schema.get("type") or "string",
            "description": description,
        }
    return parameters
