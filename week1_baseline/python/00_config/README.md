# 00 · Configuration (Python)

Python port of `week1_baseline/ruby/00_config`. Same behaviour, same
`.boukensha/` config contract, same schema — different language.

We want to be able to manage all configurations from an external file eg.
`~/.boukensha/settings.yaml`, with a dedicated class to handle configuration
eg. `boukensha.Config`. As we add configuration in each iteration we will be
updating the configuration schema and class. We can hardcode defaults but we
should not hardcode configurable values.

Configuration is organised by **task** — a role in the agentic loop bound to its
own LLM. week1_baseline only drives a single `player` task (the main loop), but
a more advanced loop will assign different LLMs to different tasks.

## Design Considerations

We want to use the standard library as much as possible. Two dependencies are
unavoidable: `pyyaml` (Python has no stdlib YAML parser) and `python-dotenv`
(the equivalent of Ruby's `dotenv` gem, for loading `.env` files).

## Code

| File | Purpose |
|------|---------|
| `boukensha/config.py` | `Config` class |
| `boukensha/tasks/base.py` | `Task` dataclass (provider/model + prompt resolution) |
| `boukensha/tasks/player.py` | the `PLAYER` task (the main loop) |
| `boukensha/__init__.py` | package exports |
| `prompts/system.md` | default system prompt shipped with the library |
| `examples/example.py` | runnable smoke-test |

---

## Config directory resolution

The class looks for a `.boukensha/` directory in this order:

1. **`BOUKENSHA_DIR` env var** — set this to point at any directory you like.
2. **`~/.boukensha`** — the default location for a real install.

## Config directory structure

```
.boukensha/
  .env                 # stores credentials eg. LLM APIs (never committed to repo)
  settings.yaml        # all non-secret settings
  prompts/
    <task>/
      system.md        # per-task override for the default system prompt (optional)
```

---

## Tasks

Where Ruby uses an abstract `Tasks::Base` with class-method-only subclasses,
the Python port uses a small frozen dataclass: `Task` is stateless, its
methods take the task's `settings` dict, and each task kind is an *instance*
rather than a subclass. `boukensha.PLAYER` is the only one for now. Future
steps add per-turn ceilings (`max_iterations`, `max_turn_tokens`,
`max_output_tokens`, `compaction_threshold`) — these are **not** read yet.

`Config.tasks()` returns the raw dict from `settings.yaml` under `tasks:`.
Pass a name to look up a specific task's settings dict, then pass it to the
task:

```python
PLAYER.provider(config.tasks("player"))
PLAYER.system_prompt(config.tasks("player"),
                     user_prompts_dir=config.user_prompts_dir,
                     default_prompts_dir=Config.PROMPTS_DIR)
```

Keys are strings only — `tasks("player")`, `dig("mud", "host")` — matching what
`yaml.safe_load` returns. There is no Ruby-style symbol/string duality.

## System prompt resolution

Per task, `PLAYER.system_prompt` is resolved in this order:

1. **`.boukensha/prompts/<task>/system.md`** — used when the task's
   `prompt_override.system` is `true` and the file exists.
2. **`prompts/system.md`** — the default system prompt shipped with the library.

## Configuration Schema

- `tasks`: a map of task name → task config (provider, model, prompt_override).
- `tasks.<name>.prompt_override.system`: when `true`, the task's
  `.boukensha/prompts/<name>/system.md` overrides the default system prompt.
- `mud`: MUD connection information for the main player.

```yaml
tasks:
  player:
    provider: anthropic        # provider name (string)
    model: claude-haiku-4-5
    prompt_override:
      system: true
mud:
  host: localhost
  port: 4000
  username: dummy
  password: helloworld
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r week1_baseline/python/00_config/requirements.txt
```

## Run Example

With the venv active:

```bash
./week1_baseline/python/bin/00_config
```

Expected output (values from your `.boukensha/`):

```
=== Boukensha Step 0: Configuration ===

Config dir:     /home/andrew/Sites/Claude-Code-Camp/.boukensha
Tasks:          player

-- player task --
Provider:       anthropic
Model:          claude-haiku-4-5
Prompt override?True
System prompt:  You are a MUD Journay Player Agent. You are playing the MUD ...

MUD host:       localhost:4000
MUD user:       dummy

API key set?    True

<boukensha.Config dir=/home/andrew/Sites/Claude-Code-Camp/.boukensha tasks=player>
```

## Considerations

Carried over from the Ruby step — observed, but deliberately not fixed since
future steps will change them anyway:

- The default prompt `prompts/system.md` should be scoped per task eg.
  `prompts/<task>/system.md`.
- The settings file should accept `.yml` or `.yaml`; right now only `.yaml`.
- There is no graceful "file not found" path for prompts — a missing prompt
  resolves to `None` rather than reporting anything.
