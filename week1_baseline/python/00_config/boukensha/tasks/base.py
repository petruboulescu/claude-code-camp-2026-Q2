import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Task:
    """A role in the agentic loop, bound to its own LLM.

    Stateless: every method takes the task's ``settings`` dict, as read from
    ``settings.yaml`` under ``tasks.<name>``.
    """

    name: str

    def provider(self, settings):
        value = self._fetch(settings, "provider")
        if not value:
            raise ValueError(f"tasks.{self.name}.provider is required in settings.yaml")
        return value

    def model(self, settings):
        value = self._fetch(settings, "model")
        if not value:
            raise ValueError(f"tasks.{self.name}.model is required in settings.yaml")
        return value

    def prompt_override(self, settings, prompt="system"):
        node = self._fetch(settings, "prompt_override")
        if not isinstance(node, dict):
            return False

        return node.get(prompt) is True

    def prompt(self, settings, name="system", user_prompts_dir=None, default_prompts_dir=None):
        if self.prompt_override(settings, name):
            text = self._read_user_prompt(name, user_prompts_dir)
            if text:
                return text

        return self._read_default_prompt(name, default_prompts_dir)

    def system_prompt(self, settings, user_prompts_dir=None, default_prompts_dir=None):
        return self.prompt(
            settings,
            "system",
            user_prompts_dir=user_prompts_dir,
            default_prompts_dir=default_prompts_dir,
        )

    # ---------- private ---------------------------------------------------

    @staticmethod
    def _fetch(settings, key):
        return settings.get(key) if isinstance(settings, dict) else None

    def _read_user_prompt(self, prompt_name, user_prompts_dir):
        if not user_prompts_dir:
            return None

        return self._read_file(os.path.join(user_prompts_dir, self.name, f"{prompt_name}.md"))

    def _read_default_prompt(self, prompt_name, default_prompts_dir):
        if not default_prompts_dir:
            return None

        return self._read_file(os.path.join(default_prompts_dir, f"{prompt_name}.md"))

    @staticmethod
    def _read_file(path):
        if not os.path.exists(path):
            return None

        with open(path, encoding="utf-8") as f:
            return f.read().strip()
