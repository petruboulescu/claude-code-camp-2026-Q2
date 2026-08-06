import os
from pathlib import Path

import yaml
from dotenv import load_dotenv


class Config:
    """Reads the .boukensha config directory (.env + settings.yaml)."""

    # The .boukensha config directory is resolved in this order:
    #   1. BOUKENSHA_DIR environment variable (set before loading .env)
    #   2. ~/.boukensha  (default)
    DEFAULT_DIR = str(Path.home() / ".boukensha")

    # Default prompts shipped alongside the library code.
    PROMPTS_DIR = str(Path(__file__).resolve().parent / "prompts")

    def __init__(self):
        self.dir = self._resolve_dir()
        self._load_env()
        self.settings = self._load_settings()

    # ---------- tasks -----------------------------------------------------

    def tasks(self, name=None):
        """With no argument: the full tasks dict from settings.yaml.

        With a name: that task's settings dict, e.g. tasks("player").
        """
        all_tasks = self.dig("tasks") or {}
        return all_tasks.get(name) if name else all_tasks

    @property
    def user_prompts_dir(self):
        """The user's prompts directory for task prompt overrides."""
        return os.path.join(self.dir, "prompts")

    # ---------- MCP servers -----------------------------------------------

    @property
    def mcp_servers(self):
        """Return normalized stdio MCP server configuration."""
        raw_servers = self.dig("mcp_servers")
        if raw_servers is None:
            return {}
        if not isinstance(raw_servers, dict):
            raise ValueError("mcp_servers must be a mapping")

        servers = {}
        for name, raw_entry in raw_servers.items():
            entry = raw_entry if isinstance(raw_entry, dict) else {}
            args = entry.get("args") or []
            env = entry.get("env") or {}
            if not isinstance(args, list):
                raise ValueError(f"mcp_servers.{name}.args must be a list")
            if not isinstance(env, dict):
                raise ValueError(f"mcp_servers.{name}.env must be a mapping")
            required = entry.get("required")
            prefix = entry.get("prefix")
            servers[str(name)] = {
                "command": str(entry.get("command") or ""),
                "args": [str(value) for value in args],
                "env": {str(key): str(value) for key, value in env.items()},
                "prefix": None if prefix is None else str(prefix),
                "required": True if required is None else bool(required),
            }
        return servers

    # ---------- low-level helpers -----------------------------------------

    def dig(self, *keys):
        """Fetch a nested key path from settings, e.g. dig("mud", "host")."""
        node = self.settings
        for key in keys:
            if not isinstance(node, dict):
                return None
            node = node.get(key)
        return node

    def __str__(self):
        return f"<boukensha.Config dir={self.dir} tasks={','.join(self.tasks().keys())}>"

    def __repr__(self):
        return str(self)

    # ---------- private ---------------------------------------------------

    def _resolve_dir(self):
        raw = os.environ.get("BOUKENSHA_DIR", self.DEFAULT_DIR)
        return os.path.abspath(os.path.expanduser(raw))

    def _load_env(self):
        env_file = os.path.join(self.dir, ".env")
        if os.path.exists(env_file):
            load_dotenv(env_file)

    def _load_settings(self):
        settings_file = os.path.join(self.dir, "settings.yaml")
        if not os.path.exists(settings_file):
            return {}

        with open(settings_file, encoding="utf-8") as f:
            return yaml.safe_load(f.read()) or {}
