import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boukensha import (  # noqa: E402
    Anthropic,
    Client,
    Config,
    Context,
    Gemini,
    Ollama,
    OllamaCloud,
    OpenAI,
    PLAYER,
    PromptBuilder,
    Registry,
)

# Override the config directory so the example works from the repo root.
# In real usage a user's ~/.boukensha is picked up automatically.
os.environ.setdefault(
    "BOUKENSHA_DIR",
    str(Path(__file__).resolve().parents[4] / ".boukensha"),
)

config = Config()
player_settings = config.tasks("player")
system_prompt = PLAYER.system_prompt(
    player_settings,
    user_prompts_dir=config.user_prompts_dir,
    default_prompts_dir=Config.PROMPTS_DIR,
)

ctx = Context(task=PLAYER, system=system_prompt)
registry = Registry(ctx)

registry.tool(
    "read_file",
    description="Read the contents of a file from disk",
    parameters={
        "path": {
            "type": "string",
            "description": "The file path to read",
        }
    },
    func=lambda path: Path(path).read_text(encoding="utf-8"),
)

registry.tool(
    "list_directory",
    description="List files in a directory",
    parameters={
        "path": {
            "type": "string",
            "description": "The directory path to list",
        }
    },
    func=lambda path: "\n".join(
        entry.name for entry in Path(path).iterdir() if not entry.name.startswith(".")
    ),
)

ctx.add_message("user", "What files are in the current directory?")

provider = PLAYER.provider(player_settings)
model = PLAYER.model(player_settings)

if provider == "anthropic":
    backend = Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
        model=model,
    )
elif provider == "openai":
    backend = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        model=model,
    )
elif provider == "gemini":
    backend = Gemini(
        api_key=os.environ["GEMINI_API_KEY"],
        model=model,
    )
elif provider == "ollama":
    backend = Ollama(model=model)
elif provider == "ollama_cloud":
    backend = OllamaCloud(
        api_key=os.environ["OLLAMA_API_KEY"],
        model=model,
    )
else:
    raise ValueError(f"Unsupported provider for player task: {provider}")

builder = PromptBuilder(ctx, backend)
client = Client(builder)

print("=== Boukensha Step 4: API Client ===")
print()
print(f"Config: {config}")
print(f"Provider: {provider}")
print(f"Model: {model}")
print(f"Sending request to {builder.url}...")
print()

response = client.call()
print("Raw response:")
print(json.dumps(response, indent=2))
