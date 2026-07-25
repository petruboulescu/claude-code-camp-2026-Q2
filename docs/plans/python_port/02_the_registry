# Python Port Plan — 02_the_registry

Port `week1_baseline/ruby/02_the_registry` to
`week1_baseline/python/02_the_registry` as the next self-contained Python
snapshot after `week1_baseline/python/01_struct_skeleton`.

Current starting point: `week1_baseline/python/02_the_registry` has already
been seeded by copying the Python `01_struct_skeleton` snapshot. This plan is
therefore a delta port only.

This step stays intentionally iterative:

- keep the Python `01_struct_skeleton` behavior, file layout, and APIs unless
  the Ruby `02_the_registry` step explicitly changes them
- add the minimal dispatch layer only: `Registry` plus `UnknownToolError`
- route tool registration and execution through the registry, while keeping the
  context-owned tool table for now
- keep the example script as the smoke test, just like the Ruby step

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/02_the_registry/README.md` | spec for this step: registry responsibilities, dispatch flow, expected output |
| `week1_baseline/ruby/02_the_registry/lib/boukensha.rb` | top-level require/export surface |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/config.rb` | same config contract as previous steps; copy forward behavior unchanged |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/tasks/base.rb` | same task API + prompt resolution as previous steps; copy forward behavior unchanged |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/tasks/player.rb` | same concrete player task |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/tool.rb` | same tool struct as step `01_struct_skeleton` |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/message.rb` | same message struct as step `01_struct_skeleton` |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/context.rb` | same context shape as step `01_struct_skeleton`; tools still live on context in this step |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/registry.rb` | new `Registry` class: register tools and dispatch calls |
| `week1_baseline/ruby/02_the_registry/lib/boukensha/errors.rb` | new Boukensha-specific error types, currently `UnknownToolError` |
| `week1_baseline/ruby/02_the_registry/examples/example.rb` | runnable smoke test for registry registration, dispatch, and unknown-tool handling |
| `week1_baseline/ruby/02_the_registry/Gemfile` / `Gemfile.lock` | dependency list; still only config-related dependencies |

Also read the previous Python port for carry-forward decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/01_struct_skeleton/README.md` | prior Python step contract and design choices |
| `week1_baseline/python/01_struct_skeleton/boukensha/__init__.py` | current export surface |
| `week1_baseline/python/01_struct_skeleton/boukensha/config.py` | baseline `Config` implementation to copy forward |
| `week1_baseline/python/01_struct_skeleton/boukensha/tasks/base.py` | baseline `Task` implementation |
| `week1_baseline/python/01_struct_skeleton/boukensha/tasks/player.py` | baseline `PLAYER` task |
| `week1_baseline/python/01_struct_skeleton/boukensha/tool.py` | baseline immutable `Tool` dataclass |
| `week1_baseline/python/01_struct_skeleton/boukensha/message.py` | baseline immutable `Message` dataclass |
| `week1_baseline/python/01_struct_skeleton/boukensha/context.py` | baseline mutable `Context` class |
| `week1_baseline/python/01_struct_skeleton/examples/example.py` | prior example style and output shape |

Also inspect the copied snapshot you are about to finish:

| File | Purpose |
|------|---------|
| `week1_baseline/python/02_the_registry/examples/example.py` | currently still step-1 behavior; needs to be rewritten around the registry |
| `week1_baseline/python/02_the_registry/README.md` | currently still describes step 1; needs to be updated to registry semantics |
| `week1_baseline/python/02_the_registry/boukensha/__init__.py` | should expand to export `Registry` and `UnknownToolError` |

## Behavior to preserve exactly

From the Ruby `02_the_registry` step:

1. **Config behavior is unchanged from prior steps**: same config dir
   resolution, `.env` loading, `settings.yaml` handling, `tasks()` lookup,
   `dig()`, and MUD defaults.
2. **Task behavior is unchanged from prior steps**: same provider/model
   requirements, same prompt override logic, same system prompt resolution.
3. **`Tool`, `Message`, and `Context` remain conceptually unchanged** from
   `01_struct_skeleton`.
4. **Registry owns the registration API**: callers define tools via
   `registry.tool(...)`, not by constructing and registering directly on
   `Context` in the example flow.
5. **Context still stores the registered tools in this step**: the registry is
   only a dispatcher facade right now, not the canonical backing store.
6. **`dispatch(name, args)` looks up by tool name** using string keys.
7. **Unknown tool names raise a dedicated error** rather than failing
   silently or returning `None`.
8. **Dispatch passes named arguments into the stored callable** using the
   provided argument map.
9. **Example parity**: the Python example should register `move` and `shout`,
   print both tools from the context, dispatch each tool, and demonstrate
   `UnknownToolError` by attempting `flee`.
10. **This step still stops short of agent orchestration**: we are only adding
    a harness-friendly registry boundary.

## Python-specific decisions to carry forward

- **Keep the `01_struct_skeleton` Python API shape**. Do not regress toward
  Ruby class patterns just because `Registry` is a class.
- **Keep `Tool` as the stored callable record** with `func` as the callable
  field name.
- **Keep string-keyed arguments at the public registry boundary** because a
  model/tool API will naturally produce JSON-like dicts.
- **Do not redesign `Context.tools` yet**. Ruby explicitly notes this is not
  the final shape, and the plan should preserve that intermediate state.
- **Keep this step self-contained** under
  `week1_baseline/python/02_the_registry/`, just like the Ruby snapshots.

## Proposed target layout

```
week1_baseline/python/02_the_registry/
  requirements.txt
  README.md
  boukensha/
    __init__.py
    config.py            # copied forward unchanged
    tool.py              # copied forward unchanged
    message.py           # copied forward unchanged
    context.py           # copied forward, likely unchanged or only repr-touched
    errors.py            # UnknownToolError
    registry.py          # Registry class
    tasks/
      __init__.py
      base.py            # copied forward unchanged
      player.py
  prompts/
    system.md
  examples/
    example.py
week1_baseline/python/bin/02_the_registry
```

The structure should continue mirroring Ruby: each step is a standalone Python
snapshot, not an in-place mutation of one shared package.

## API plan

### `UnknownToolError`

Add a step-local error type:

```python
class UnknownToolError(Exception):
    pass
```

Notes:

- Keep it in `boukensha/errors.py`, matching the Ruby teaching structure.
- Export it from `boukensha/__init__.py`.
- The message should match Ruby intent closely:
  `No tool registered as 'flee'`

### `Registry`

Use a small mutable class holding a context reference:

```python
class Registry:
    def __init__(self, context: Context):
        self._context = context

    def tool(self, name: str, *, description: str,
             parameters: dict[str, dict] | None = None,
             func: Callable[..., str]) -> Tool:
        ...

    def dispatch(self, name: str, args: Mapping[str, object] | None = None) -> object:
        ...
```

Required behavior:

- `tool(...)` constructs a `Tool`, registers it on the context, and returns it.
- `dispatch(...)` looks up the tool in `context.tools` using `str(name)`.
- Missing tool raises `UnknownToolError`.
- Provided args default to `{}`.
- Dispatch calls `tool.func(**args)` directly in Python.

Notes:

- Ruby converts string keys to symbol keys before invoking the block. Python
  does not need that translation because keyword arguments are already string
  keyed.
- Do not introduce validation, schema enforcement, or async dispatch in this
  step.
- Do not move tool storage out of `Context` yet, even if it is architecturally
  cleaner. The Ruby README explicitly leaves that correction for later.

## README / example plan

The copied Python `02_the_registry` files still describe step 1. Update them
to reflect the actual registry delta.

### README

Rewrite `week1_baseline/python/02_the_registry/README.md` so it explains:

- the registry's two responsibilities: storing tools and dispatching them
- that registration now goes through `Registry.tool(...)`
- that dispatch raises `UnknownToolError` for unknown tool names
- that tools still remain attached to the context in this transitional step

Expected output shape should follow Ruby closely, but with Python reprs:

```text
=== Boukensha Step 2: Tool Registry ===

Context: <Context task=player turns=0 tools=2>
Tools:
  <Tool name=move ...>
  <Tool name=shout ...>

Dispatching 'shout' with message='dragon spotted'...
Result: DRAGON SPOTTED

Dispatching 'move' with direction='north'...
Result: You move north into a torch-lit corridor.

UnknownToolError caught: No tool registered as 'flee'
```

### Example flow

The Python example should do this, in order:

1. Set `BOUKENSHA_DIR` to the repo `.boukensha` for local smoke testing.
2. Instantiate `Config`.
3. Load `player` settings via `config.tasks("player")`.
4. Resolve the player system prompt via `PLAYER.system_prompt(...)`.
5. Build `Context(task=PLAYER, system=system_prompt)`.
6. Build `Registry(ctx)`.
7. Register `move` through `registry.tool(...)`.
8. Register `shout` through `registry.tool(...)`.
9. Print config, context, and all registered tools from `ctx.tools.values()`.
10. Dispatch `shout` with `{"message": "dragon spotted"}` and print the result.
11. Dispatch `move` with `{"direction": "north"}` and print the result.
12. Attempt `registry.dispatch("flee")`, catch `UnknownToolError`, and print
    the error message.

## Implementation order

1. **Treat the copied `01_struct_skeleton` snapshot as the baseline**.
   Keep `Config`, `Task`, `PLAYER`, `Tool`, `Message`, `Context`, prompts, and
   requirements unless this step needs a targeted update.
2. **Add `errors.py`**.
   Introduce `UnknownToolError`.
3. **Add `registry.py`**.
   Implement the registration facade and dispatcher.
4. **Expand package exports**.
   Update `boukensha/__init__.py` to export `Registry` and
   `UnknownToolError` alongside the existing API.
5. **Update the example**.
   Replace the step-1 direct `ctx.register_tool(...)` flow with registry-based
   registration and dispatch.
6. **Add the Python wrapper script**.
   Follow the same pattern as `python/bin/01_struct_skeleton`, but target this
   step.
7. **Rewrite the Python README**.
   Preserve the Ruby teaching intent while documenting the Python callable and
   exception choices explicitly.

## Checks to run after the port

1. Run `./week1_baseline/python/bin/02_the_registry`.
2. Confirm both tools are visible through `ctx.tools`.
3. Confirm `registry.dispatch("shout", {"message": "dragon spotted"})`
   returns uppercase text.
4. Confirm `registry.dispatch("move", {"direction": "north"})` returns the
   movement string.
5. Confirm `registry.dispatch("flee")` raises and is caught as
   `UnknownToolError`.

## Explicitly defer for later steps

- Moving the full registered-tool table off `Context` and onto `Registry`
- Provider/API serialization of tools
- Tool-call IDs, structured tool-use messages, or agent loop integration
- Argument validation against `Tool.parameters`
- Any architectural cleanup beyond what Ruby `02_the_registry` already does
