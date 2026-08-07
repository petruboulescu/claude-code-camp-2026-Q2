import sys
from enum import Enum

from .agent import Agent
from .errors import ApiError, LoopError, TurnCancelled


class CommandResult(Enum):
    NOT_COMMAND = "not_command"
    COMMAND = "command"
    QUIT = "quit"


class Repl:
    """Persistent agent session that can be driven by any front end."""

    PROMPT = "boukensha> "
    HELP = """Commands:
  /quiet   suppress logging output
  /loud    re-enable logging output
  /clear    wipe conversation history (tools stay)
  /compact  drop oldest 40% of messages to free context
  /exit    leave the REPL
  /help    show this message"""

    def __init__(self, *, context, registry, builder, client, logger,
                 config_dir=None, provider=None, model=None, version=None,
                 api_key=None, servers=None, task_settings=None,
                 max_iterations=None, max_turn_tokens=None, max_output_tokens=None,
                 input_stream=None, output_stream=None):
        self.context = context
        self.registry = registry
        self.builder = builder
        self.client = client
        self.logger = logger
        self.task_settings = task_settings
        self.max_iterations = max_iterations
        self.max_turn_tokens = max_turn_tokens
        self.max_output_tokens = max_output_tokens
        self.config_dir = config_dir
        self.provider = provider
        self.model = model
        self.version = version
        self.api_key = api_key
        self.servers = servers
        self.input_stream = input_stream or sys.stdin
        self.output_stream = output_stream or sys.stdout
        self.turn = 0
        self._output_callback = None

    def on_output(self, callback):
        if callback is not None and not callable(callback):
            raise TypeError("output callback must be callable")
        self._output_callback = callback
        return callback

    def banner(self):
        version = self.version or "?.?.?"
        title_padding = " " * max(0, 9 - len(version))
        key_status = "✗ API key not set" if not str(self.api_key or "").strip() else "✓ API key set"
        provider = f"{self.provider or 'default'} ({self.model or 'default'})  {key_status}"
        if self.config_dir and __import__("os").path.isdir(self.config_dir):
            config = self.config_dir
        else:
            config = f"{self.config_dir or '(default)'}  ✗ directory not found"
        servers = ("  ".join(f"{name} ({count})" for name, count in self.servers.items())
                   if self.servers else "(none configured — the agent has no tools)")
        return f"""
╔══════════════════════════════════════╗
║  BOUKENSHA MUD Assistant (v{version}){title_padding}║
╚══════════════════════════════════════╝
  config:    {config}
  provider:  {provider}
  servers:   {servers}

  /quiet or /loud   toggle logging
  /clear            reset conversation history
  /compact          free context (drop oldest messages)
  /exit or /quit    leave the REPL
"""

    def handle_command(self, user_input):
        import boukensha
        if not user_input.startswith("/"):
            return CommandResult.NOT_COMMAND
        if user_input in ("/exit", "/quit"):
            self._write("Goodbye.")
            return CommandResult.QUIT
        if user_input == "/help":
            self._write(self.HELP)
        elif user_input == "/quiet":
            boukensha.quiet()
            self._write("(logging suppressed — type /loud to re-enable)")
        elif user_input == "/loud":
            boukensha.loud()
            self._write("(logging enabled)")
        elif user_input == "/clear":
            self.context.clear_messages()
            self.turn = 0
            self._write("(conversation history cleared)")
        elif user_input == "/compact":
            dropped = self.context.compact_messages()
            self._write(f"(compacted context — {dropped} messages dropped)")
        else:
            return CommandResult.NOT_COMMAND
        return CommandResult.COMMAND

    def run_turn(self, user_input, cancel_event=None):
        self.turn += 1
        self.logger.turn(n=self.turn)
        self.context.add_message("user", user_input)
        agent = Agent(context=self.context, registry=self.registry,
                      builder=self.builder, client=self.client,
                      logger=self.logger, task_settings=self.task_settings,
                      max_iterations=self.max_iterations,
                      max_turn_tokens=self.max_turn_tokens,
                      max_output_tokens=self.max_output_tokens,
                      cancel_event=cancel_event)
        try:
            result = agent.run()
            self._write()
            self._write(result)
            return result
        except TurnCancelled:
            raise
        except LoopError as error:
            self._write(f"\n[error] {error}")
        except ApiError as error:
            self._write(f"\n[error] API call failed: {error}")
        return None

    def start(self):
        self._write(self.banner())
        while True:
            if self._output_callback is None:
                self._write(self.PROMPT, end="", flush=True)
            line = self.input_stream.readline()
            if line == "":
                break
            user_input = line.strip()
            if not user_input:
                continue
            result = self.handle_command(user_input)
            if result is CommandResult.QUIT:
                break
            if result is CommandResult.COMMAND:
                continue
            self.run_turn(user_input)

    def _write(self, value="", *, end="\n", flush=False):
        if self._output_callback is not None:
            self._output_callback(str(value))
        else:
            print(value, end=end, file=self.output_stream, flush=flush)
