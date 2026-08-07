from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    role: str
    content: str
    tool_use_id: str | None = None

    def __str__(self):
        id_tag = f" [{self.tool_use_id}]" if self.tool_use_id else ""
        preview = (self.content or "")[:61]
        return f"<Message role={self.role}{id_tag} content={preview}...>"

    def __repr__(self):
        return str(self)
