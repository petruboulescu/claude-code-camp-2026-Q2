import os

from .agent import Agent
from .backends import Anthropic, Gemini, Ollama, OllamaCloud, OpenAI
from .client import Client
from .config import Config
from .context import Context
from .logger import Logger
from .prompt_builder import PromptBuilder
from .repl import Repl
from .registry import Registry
from .tasks import PLAYER
from .version import VERSION


class RunDSL:
    """The deliberately small tool-registration surface used by ``run``."""

    def __init__(self, registry):
        self._registry = registry

    def tool(self, name, *, description, parameters=None, func=None):
        """Register ``func`` directly, or return a registration decorator."""

        def register(candidate):
            if not callable(candidate):
                raise TypeError("tool function must be callable")
            self._registry.tool(
                name,
                description=description,
                parameters=parameters,
                func=candidate,
            )
            return candidate

        if func is None:
            return register
        return register(func)


def _build_backend(*, provider, api_key, model, ollama_host):
    if provider == "anthropic":
        return Anthropic(api_key=api_key, model=model)
    if provider == "openai":
        return OpenAI(api_key=api_key, model=model)
    if provider == "gemini":
        return Gemini(api_key=api_key, model=model)
    if provider == "ollama":
        return Ollama(host=ollama_host, model=model)
    if provider == "ollama_cloud":
        return OllamaCloud(api_key=api_key, model=model)

    accepted = "anthropic, openai, gemini, ollama, or ollama_cloud"
    raise ValueError(
        f"Unknown backend {provider!r}. Use {accepted}."
    )


def _default_api_key(provider):
    environment_keys = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "ollama_cloud": "OLLAMA_API_KEY",
    }
    key = environment_keys.get(provider)
    return os.environ.get(key) if key is not None else None


def run(
    *,
    task,
    system=None,
    model=None,
    backend=None,
    api_key=None,
    ollama_host="http://localhost:11434",
    log=None,
    max_output_tokens=None,
    configure=None,
):
    """Assemble and run the player agent from a concise public entry point."""

    # Imported lazily to avoid the package/submodule ``config`` name collision
    # while boukensha.__init__ is still being initialized.
    import boukensha

    cfg = boukensha.config()
    task_settings = cfg.tasks(PLAYER.name)

    if system is None:
        system = PLAYER.system_prompt(
            task_settings,
            user_prompts_dir=cfg.user_prompts_dir,
            default_prompts_dir=Config.PROMPTS_DIR,
        )
    if model is None:
        model = PLAYER.model(task_settings)
    if backend is None:
        backend = PLAYER.provider(task_settings)
    if api_key is None:
        api_key = _default_api_key(backend)

    context = Context(task=PLAYER, system=system)
    registry = Registry(context)

    if configure is not None:
        if not callable(configure):
            raise TypeError("configure must be callable")
        configure(RunDSL(registry))

    resolved_backend = _build_backend(
        provider=backend,
        api_key=api_key,
        model=model,
        ollama_host=ollama_host,
    )
    builder = PromptBuilder(context, resolved_backend)
    client = Client(builder)
    effective_max_iterations = PLAYER.max_iterations(task_settings)
    effective_max_output_tokens = (
        PLAYER.max_output_tokens(task_settings)
        if max_output_tokens is None
        else max_output_tokens
    )

    logger = None
    try:
        logger = Logger(
            log=log,
            snapshot={
                "task": PLAYER.name,
                "max_iterations": effective_max_iterations,
                "max_output_tokens": effective_max_output_tokens,
                "model": model,
                "provider": backend,
            },
        )
        agent = Agent(
            context=context,
            registry=registry,
            builder=builder,
            client=client,
            logger=logger,
            task_settings=task_settings,
            max_iterations=effective_max_iterations,
            max_output_tokens=effective_max_output_tokens,
        )
        context.add_message("user", task)
        return agent.run()
    finally:
        if logger is not None:
            logger.close()


def repl(
    *,
    system=None,
    model=None,
    backend=None,
    api_key=None,
    ollama_host="http://localhost:11434",
    log=None,
    max_output_tokens=None,
    configure=None,
):
    """Assemble and start an interactive player-agent session."""

    import boukensha

    cfg = boukensha.config()
    task_settings = cfg.tasks(PLAYER.name)

    if system is None:
        system = PLAYER.system_prompt(
            task_settings,
            user_prompts_dir=cfg.user_prompts_dir,
            default_prompts_dir=Config.PROMPTS_DIR,
        )
    if model is None:
        model = PLAYER.model(task_settings)
    if backend is None:
        backend = PLAYER.provider(task_settings)
    if api_key is None:
        api_key = _default_api_key(backend)

    context = Context(task=PLAYER, system=system)
    registry = Registry(context)

    if configure is not None:
        if not callable(configure):
            raise TypeError("configure must be callable")
        configure(RunDSL(registry))

    resolved_backend = _build_backend(
        provider=backend,
        api_key=api_key,
        model=model,
        ollama_host=ollama_host,
    )
    builder = PromptBuilder(context, resolved_backend)
    client = Client(builder)
    effective_max_iterations = PLAYER.max_iterations(task_settings)
    effective_max_output_tokens = (
        PLAYER.max_output_tokens(task_settings)
        if max_output_tokens is None
        else max_output_tokens
    )

    logger = None
    try:
        logger = Logger(
            log=log,
            snapshot={
                "task": PLAYER.name,
                "max_iterations": effective_max_iterations,
                "max_output_tokens": effective_max_output_tokens,
                "model": model,
                "provider": backend,
            },
        )
        try:
            session = Repl(
                context=context,
                registry=registry,
                builder=builder,
                client=client,
                logger=logger,
                task_settings=task_settings,
                max_iterations=effective_max_iterations,
                max_output_tokens=effective_max_output_tokens,
                config_dir=cfg.dir,
                provider=backend,
                model=model,
                version=VERSION,
                api_key=api_key,
            )
            return session.start()
        except KeyboardInterrupt:
            print("\nInterrupted.")
            return None
    finally:
        if logger is not None:
            logger.close()
