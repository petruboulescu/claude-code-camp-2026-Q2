_quiet = False
_debug = False
_config = None


def _get_config():
    global _config
    if _config is None:
        _config = Config()
    return _config


def quiet():
    global _quiet
    _quiet = True


def loud():
    global _quiet
    _quiet = False


def is_quiet():
    return _quiet


def debug():
    global _debug
    _debug = True


def is_debug():
    return _debug


from .agent import Agent
from .backends import Anthropic, Backend, Gemini, Ollama, OllamaCloud, OpenAI
from .client import Client
from .config import Config
from .context import Context
from .errors import ApiError, LoopError, UnknownToolError, UnsupportedModelError
from .logger import Logger
from .message import Message
from .prompt_builder import PromptBuilder
from .registry import Registry
from .tasks import PLAYER, Task
from .tool import Tool
from .run_dsl import RunDSL, run


# Importing the ``boukensha.config`` submodule temporarily assigns that module
# to this package's ``config`` attribute. Define the public function after the
# imports so it remains the callable runtime API.
def config():
    return _get_config()


__all__ = [
    "Agent",
    "Anthropic",
    "ApiError",
    "Backend",
    "Client",
    "Config",
    "Context",
    "Gemini",
    "LoopError",
    "Logger",
    "Message",
    "Ollama",
    "OllamaCloud",
    "OpenAI",
    "PLAYER",
    "PromptBuilder",
    "Registry",
    "RunDSL",
    "Task",
    "Tool",
    "UnknownToolError",
    "UnsupportedModelError",
    "config",
    "debug",
    "is_debug",
    "is_quiet",
    "loud",
    "quiet",
    "run",
]
