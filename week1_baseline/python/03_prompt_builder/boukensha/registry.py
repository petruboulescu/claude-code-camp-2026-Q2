from .errors import UnknownToolError
from .tool import Tool


class Registry:
    def __init__(self, context):
        self._context = context

    def tool(self, name, *, description, parameters=None, func):
        tool = Tool(
            name=str(name),
            description=description,
            parameters=parameters or {},
            func=func,
        )
        self._context.register_tool(tool)
        return tool

    def dispatch(self, name, args=None):
        tool = self._context.tools.get(str(name))
        if tool is None:
            raise UnknownToolError(f"No tool registered as '{name}'")

        return tool.func(**(args or {}))
