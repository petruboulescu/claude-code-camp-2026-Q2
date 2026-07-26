from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, dict[str, Any]]
    func: Callable[..., str]

    def __str__(self):
        preview = (self.description or "")[:41]
        return f"<Tool name={self.name} description={preview} params={list(self.parameters.keys())}>"

    def __repr__(self):
        return str(self)
