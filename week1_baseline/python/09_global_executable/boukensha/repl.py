import sys

from .agent import Agent
from .errors import ApiError, LoopError


class Repl:
    """Interactive loop over one persistent agent context."""

    PROMPT = "boukensha> "
    HELP = """Commands:
  /quiet   suppress logging output
  /loud    re-enable logging output
  /clear   wipe conversation history (tools stay)
  /exit    leave the REPL
  /help    show this message"""

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        logger,
        config_dir=None,
        provider=None,
        model=None,
        version=None,
        api_key=None,
        task_settings=None,
        max_iterations=None,
        max_output_tokens=None,
        input_stream=None,
        output_stream=None,
    ):
        self.context = context
        self.registry = registry
        self.builder = builder
        self.client = client
        self.logger = logger
        self.task_settings = task_settings
        self.max_iterations = max_iterations
        self.max_output_tokens = max_output_tokens
        self.config_dir = config_dir
        self.provider = provider
        self.model = model
        self.version = version
        self.api_key = api_key
        self.input_stream = input_stream or sys.stdin
        self.output_stream = output_stream or sys.stdout
        self.turn = 0

    def start(self):
        self._write(self._banner())

        while True:
            self._write(self.PROMPT, end="", flush=True)
            line = self.input_stream.readline()
            if line == "":
                break

            user_input = line.strip()
            if not user_input:
                continue
            if self._handle_command(user_input):
                break

    def _handle_command(self, user_input):
        import boukensha

        if user_input in ("/exit", "/quit"):
            self._write("Goodbye.")
            return True
        if user_input == "/help":
            self._write(self.HELP)
            return False
        if user_input == "/quiet":
            boukensha.quiet()
            self._write("(logging suppressed — type /loud to re-enable)")
            return False
        if user_input == "/loud":
            boukensha.loud()
            self._write("(logging enabled)")
            return False
        if user_input == "/clear":
            self.context.clear_messages()
            self.turn = 0
            self._write("(conversation history cleared)")
            return False

        self._run_turn(user_input)
        return False

    def _run_turn(self, user_input):
        self.turn += 1
        self.logger.turn(n=self.turn)
        self.context.add_message("user", user_input)

        agent = Agent(
            context=self.context,
            registry=self.registry,
            builder=self.builder,
            client=self.client,
            logger=self.logger,
            task_settings=self.task_settings,
            max_iterations=self.max_iterations,
            max_output_tokens=self.max_output_tokens,
        )
        try:
            result = agent.run()
            self._write()
            self._write(result)
        except LoopError as error:
            self._write(f"\n[error] {error}")
        except ApiError as error:
            self._write(f"\n[error] API call failed: {error}")

    def _banner(self):
        version = self.version or "?.?.?"
        title_padding = " " * max(0, 9 - len(version))
        return f"""
╔══════════════════════════════════════╗
║  BOUKENSHA MUD Assistant (v{version}){title_padding}║
╚══════════════════════════════════════╝
  config:        {self.config_dir or "(default)"}
  provider:      {self.provider or "(default)"}
  model:         {self.model or "(default)"}

  /quiet or /loud   toggle logging
  /clear            reset conversation history
  /exit or /quit    leave the REPL
"""

    def _write(self, value="", *, end="\n", flush=False):
        print(value, end=end, file=self.output_stream, flush=flush)
