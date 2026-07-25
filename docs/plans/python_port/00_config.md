# Python Port Plan — 00_config

Port `week1_baseline/ruby/00_config` to `week1_baseline/python/00_config`
(currently an empty placeholder directory). Same behavior, same
`.boukensha/` config contract, same config schema — different language.

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/00_config/README.md` | spec for this step: config dir resolution, schema, task/prompt design |
| `week1_baseline/ruby/00_config/lib/boukensha.rb` | top-level require |
| `week1_baseline/ruby/00_config/lib/boukensha/config.rb` | `Boukensha::Config`: dir resolution, `.env` loading, `settings.yaml` loading, `tasks`/`dig`/`mud_*` accessors |
| `week1_baseline/ruby/00_config/lib/boukensha/tasks/base.rb` | abstract `Tasks::Base`: class-method-only API — `provider`, `model`, `prompt_override?`, `prompt`/`system_prompt` resolution |
| `week1_baseline/ruby/00_config/lib/boukensha/tasks/player.rb` | concrete `Tasks::Player` (`task_name = "player"`) |
| `week1_baseline/ruby/00_config/prompts/system.md` | default system prompt shipped with the library |
| `week1_baseline/ruby/00_config/examples/example.rb` | runnable smoke test exercising the whole API |
| `week1_baseline/ruby/00_config/Gemfile` / `Gemfile.lock` | dependency list (only `dotenv`) |
| `week1_baseline/ruby/bin/00_config` | wrapper script: `cd` into the step dir, run the example |
| `.boukensha/settings.yaml` | live settings this step reads (schema: `tasks.*`, `mud.*`) — not ported, just consumed |
| `.boukensha/prompts/player/system.md` | live per-task prompt override — not ported, just consumed |

The `.boukensha/` directory at the repo root is shared across languages —
the Python port must resolve and read it exactly like the Ruby version does,
with no changes to its layout or schema.

## Behavior to preserve exactly

1. **Config dir resolution**: `BOUKENSHA_DIR` env var, else `~/.boukensha`.
2. **`.env` loading**: only if `<dir>/.env` exists, loaded before settings.
3. **`settings.yaml` loading**: missing file → `{}`, not an error.
4. **`tasks(name=None)`**: no-arg returns the full `tasks:` map; with a name,
   returns that task's settings dict.
5. **`dig(*keys)`**: safe nested lookup into `settings`, returns `None` on
   any missing key instead of raising.
6. **`mud_host`/`mud_port`/`mud_username`/`mud_password`**: same defaults
   (`localhost`, `4000`, `None`, `None`).
7. **`Tasks.Base`**: never instantiated; `task_name` is abstract (raises if
   unimplemented); `provider`/`model` raise if missing from settings;
   `prompt_override?(settings, prompt="system")` reads
   `prompt_override.<prompt>` and is `True` only when it's exactly `true`.
8. **Prompt resolution order**: user override
   (`<user_prompts_dir>/<task_name>/<name>.md`) only if `prompt_override?`
   is true **and** the file exists; otherwise the default
   (`<default_prompts_dir>/<name>.md`); file contents are stripped.
9. **`Tasks.Player`**: `task_name == "player"`, nothing else.
10. **`example.rb` parity**: a Python example script producing the same
    shape of output (config dir, tasks list, provider/model/override/prompt
    preview, mud host/port/user, whether the API key is set, repr of the
    config object).
11. **`bin/00_config` wrapper**: same `cd` + run pattern, adapted to the
    Python runner.

## Proposed target layout

```
week1_baseline/python/00_config/
  requirements.txt
  README.md
  boukensha/
    __init__.py
    config.py          # Config class
    tasks/
      __init__.py       # exports Task, PLAYER
      base.py            # Task dataclass (see "Task API shape" below)
      player.py           # PLAYER = Task(name="player")
  prompts/
    system.md
  examples/
    example.py
week1_baseline/python/bin/00_config   # wrapper script
```

This mirrors the Ruby step's directory shape 1:1 (`lib/` → `boukensha/`,
`prompts/`, `examples/`) — confirmed intentional: **each future step
(`01_...`, `02_...`) gets its own `week1_baseline/python/NN_name/` folder**,
same as Ruby's per-step directories, rather than one evolving package. Every
step is a self-contained snapshot in both languages, kept easy to diff
against its Ruby counterpart.

## Decisions

- **Task API shape** — idiomatic Python, not a Ruby mirror: `Task` is a
  small frozen dataclass (not a never-instantiated class-method bag):

  ```python
  # boukensha/tasks/base.py
  @dataclass(frozen=True)
  class Task:
      name: str

      def provider(self, settings: dict) -> str: ...
      def model(self, settings: dict) -> str: ...
      def prompt_override(self, settings: dict, prompt: str = "system") -> bool: ...
      def system_prompt(self, settings: dict, *, user_prompts_dir=None,
                         default_prompts_dir=None) -> str | None: ...

  # boukensha/tasks/player.py
  PLAYER = Task(name="player")
  ```

  Call site: `PLAYER.provider(settings)` instead of Ruby's
  `Tasks::Player.provider(settings)`. Same behavior (section
  "Behavior to preserve exactly" above still applies), different shape —
  `name` is a plain field instead of an abstract classmethod, and future
  task kinds are just more `Task(...)` instances rather than more
  subclasses.
- **Keys are strings only** — `tasks("player")`, `dig("mud", "host")`, etc.
  No Ruby-style symbol/string duality; matches what `yaml.safe_load`
  already returns.
- **Dependencies**: `pyyaml` (no stdlib YAML parser in Python) and
  `python-dotenv` (direct equivalent of the `dotenv` gem), listed in
  `requirements.txt`.
- **Tooling**: plain `pip` + `venv` + `requirements.txt`. No `uv`, no
  `pyproject.toml`/build backend, no linter pinned — simplest possible
  setup, intentionally not reusing `week0_explore/circlemud-world-parser`'s
  `uv`/`hatchling`/`ruff` stack. Python version not pinned; assume a
  reasonably current CPython 3 (3.11+) unless you'd rather specify one.
- **Tests**: parity with the Ruby step — no `pytest` suite yet, just
  `examples/example.py` as the runnable smoke test.
- **Wrapper script**: `week1_baseline/python/bin/00_config` runs
  `python3 examples/example.py` directly (assumes a venv with
  `requirements.txt` installed is already active/on `PATH`) — no `uv run`.
