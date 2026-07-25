# Python Port Plan — 01_struct_skeleton

Port `week1_baseline/ruby/01_struct_skeleton` to
`week1_baseline/python/01_struct_skeleton` as the next self-contained Python
snapshot after `week1_baseline/python/00_config`.

Current starting point: `week1_baseline/python/01_struct_skeleton` has already
been seeded by copying the previous Python `00_config` snapshot. This plan is
therefore a delta port only.

This step stays intentionally iterative:

- keep the `00_config` Python behavior and directory shape
- carry forward `Config`, `Task`, and `PLAYER` with only the minimum changes
  needed for this step
- add the three new data structures only: `Tool`, `Message`, `Context`
- keep the example script as the smoke test, just like the Ruby step

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/01_struct_skeleton/README.md` | spec for this step: what `Tool`, `Message`, and `Context` represent |
| `week1_baseline/ruby/01_struct_skeleton/lib/boukensha.rb` | top-level require/export surface |
| `week1_baseline/ruby/01_struct_skeleton/lib/boukensha/config.rb` | same config contract as step `00_config`; copy forward behavior unchanged |
| `week1_baseline/ruby/01_struct_skeleton/lib/boukensha/tasks/base.rb` | same task API + prompt resolution as step `00_config`; copy forward behavior unchanged |
| `week1_baseline/ruby/01_struct_skeleton/lib/boukensha/tasks/player.rb` | same concrete player task |
| `week1_baseline/ruby/01_struct_skeleton/lib/boukensha/tool.rb` | `Boukensha::Tool` struct and its string representation |
| `week1_baseline/ruby/01_struct_skeleton/lib/boukensha/message.rb` | `Boukensha::Message` struct and its string representation |
| `week1_baseline/ruby/01_struct_skeleton/lib/boukensha/context.rb` | `Boukensha::Context`: task, system, messages, tools, register/add helpers |
| `week1_baseline/ruby/01_struct_skeleton/examples/example.rb` | runnable smoke test for the whole step |
| `week1_baseline/ruby/01_struct_skeleton/Gemfile` / `Gemfile.lock` | dependency list; still only `dotenv` via config loading |
| `week1_baseline/ruby/bin/01_struct` | wrapper script: `cd` into the step dir, run the example |

Also read the previous Python port for carry-forward decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/00_config/README.md` | prior Python step contract and design choices |
| `week1_baseline/python/00_config/boukensha/config.py` | baseline `Config` implementation to copy forward |
| `week1_baseline/python/00_config/boukensha/tasks/base.py` | baseline `Task` dataclass implementation |
| `week1_baseline/python/00_config/boukensha/tasks/player.py` | baseline `PLAYER` task |
| `week1_baseline/python/00_config/examples/example.py` | prior example style and output shape |

## Behavior to preserve exactly

From the Ruby `01_struct_skeleton` step:

1. **Config behavior is unchanged from `00_config`**: same config dir
   resolution, `.env` loading, `settings.yaml` handling, `tasks()` lookup,
   `dig()`, and MUD defaults.
2. **Task behavior is unchanged from `00_config`**: same provider/model
   requirements, same prompt override logic, same system prompt resolution.
3. **`Tool` fields**: name, description, parameters, block/callable.
4. **`Tool` registry key**: tools are stored in context by `tool.name`.
5. **`Message` fields**: role, content, tool_use_id.
6. **`Message.tool_use_id` is optional**: absent for normal user/assistant
   turns, present for tool-result messages.
7. **`Context` fields**: task, system, messages, tools.
8. **`Context` starts empty**: no messages, no tools on initialization.
9. **`Context.register_tool(tool)`** inserts/replaces by tool name.
10. **`Context.add_message(role, content, tool_use_id=None)`** appends a new
    message object to history.
11. **`Context.tool_count` / `turn_count`** report current collection sizes.
12. **Example parity**: the Python example should build the same minimal
    context, register the same `move` tool, add the same two messages, and
    print the same shape of summary output.

## Python-specific decisions to carry forward

- **Keep the `00_config` Python API shape**. Do not regress toward Ruby's
  class-method style just because this step adds new structs.
- **Keep `Task` as a frozen dataclass instance** (`PLAYER = Task(name="player")`).
- **Keep string-only keys** in config/settings access.
- **Keep plain `requirements.txt` + `venv` setup**. No packaging/tooling jump
  in this step.
- **Keep this step self-contained** under
  `week1_baseline/python/01_struct_skeleton/`, just like the Ruby snapshots.

## Proposed target layout

```
week1_baseline/python/01_struct_skeleton/
  requirements.txt
  README.md
  boukensha/
    __init__.py
    config.py            # copied/adapted from python/00_config
    tool.py              # Tool dataclass
    message.py           # Message dataclass
    context.py           # Context class
    tasks/
      __init__.py
      base.py            # copied/adapted from python/00_config
      player.py
  prompts/
    system.md
  examples/
    example.py
week1_baseline/python/bin/01_struct_skeleton
```

The structure mirrors Ruby again. This matters because later steps should be
ported as independent snapshots, not by mutating one shared Python package in
place.

## Data structure plan

### `Tool`

Ruby uses a `Struct` with a stored `block`. In Python, use a small dataclass:

```python
@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    parameters: dict[str, dict]
    func: Callable[..., str]
```

Notes:

- Name the callable field `func` rather than `block`; that is the more natural
  Python spelling.
- Behavior still matches Ruby: the callable is stored on the object and is not
  invoked by `Context`.
- `__str__` should mimic Ruby's summary:
  `<Tool name=move description=Move the player ... params=['direction']>`
- Parameters stay schema-like dictionaries; do not introduce a richer typed
  parameter model yet.

### `Message`

Use a dataclass:

```python
@dataclass(frozen=True)
class Message:
    role: str
    content: str
    tool_use_id: str | None = None
```

Notes:

- Keep `role` as a plain string for now; do not introduce enums in this step.
- `__str__` should preserve Ruby's compact preview format and optional
  `tool_use_id` tag.
- Content preview truncation can be approximate; parity of intent matters more
  than byte-for-byte matching.

### `Context`

Use a normal class, not a dataclass. It has mutable collections.

```python
class Context:
    def __init__(self, task: Task | None, system: str | None = None):
        self.task = task
        self.system = system
        self.messages: list[Message] = []
        self.tools: dict[str, Tool] = {}
```

Required methods/properties:

- `register_tool(tool)`
- `add_message(role, content, tool_use_id=None)`
- `tool_count`
- `turn_count`
- `__str__`

Notes:

- `register_tool` should overwrite an existing tool with the same name, just
  like Ruby hash assignment.
- `add_message` should construct the `Message` object internally rather than
  requiring callers to instantiate it themselves.
- `__str__` should surface the task name, turn count, and tool count:
  `<Context task=player turns=2 tools=1>`

## Implementation order

1. **Treat the copied `00_config` snapshot as the baseline**.
   Keep `Config`, `Task`, `PLAYER`, prompt file, and requirements unless this
   step needs a targeted change.
2. **Expand package exports**.
   Update `boukensha/__init__.py` to export `Config`, `Task`, `PLAYER`,
   `Tool`, `Message`, and `Context`.
3. **Add `tool.py`**.
   Implement the immutable tool record and its readable `__str__`.
4. **Add `message.py`**.
   Implement the immutable message record and its readable `__str__`.
5. **Add `context.py`**.
   Implement mutable runtime state, registration, message append helpers, and
   summary formatting.
6. **Update the example**.
   Mirror the Ruby `examples/example.rb` flow exactly, but using Python
   objects and the Python `PLAYER` API.
7. **Add the Python wrapper script**.
   Follow the same pattern as `python/bin/00_config`, but target this step.
8. **Write the Python README**.
   Preserve the Ruby teaching intent while documenting the Python dataclass
   choices explicitly.

## Example target flow

The Python example should do this, in order:

1. Set `BOUKENSHA_DIR` to the repo `.boukensha` for local smoke testing.
2. Instantiate `Config`.
3. Load `player` settings via `config.tasks("player")`.
4. Resolve the player system prompt via `PLAYER.system_prompt(...)`.
5. Build `Context(task=PLAYER, system=system_prompt)`.
6. Register one `Tool` named `move` with the same description and parameter
   schema as Ruby.
7. Add the same user and assistant messages.
8. Print config, context, tool, and messages in the same general layout as the
   Ruby example.

## Dependencies

- `pyyaml`
- `python-dotenv`

No new third-party dependencies are needed for this step.

## Verification plan

- Run `./week1_baseline/python/bin/01_struct_skeleton`.
- Confirm the script prints:
  - the config summary
  - the context summary with `task=player turns=2 tools=1`
  - the registered `move` tool summary
  - two message summaries
- Manually verify that `Tool.func` is stored but not executed during the smoke
  test, matching the Ruby example.

## Non-goals for this step

- No actual LLM API integration yet.
- No tool execution loop yet.
- No serialization layer for Anthropic/OpenAI message formats yet.
- No validation framework for tool parameters yet.
- No test suite beyond the runnable example; keep parity with the Ruby step.
