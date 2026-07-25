# 02 · The Tool Registry (Python)

Python port of `week1_baseline/ruby/02_the_registry`. This step keeps the
configuration and runtime data structures from `01_struct_skeleton`, but adds
the first dedicated tool dispatch layer:

- `boukensha.Registry`
- `boukensha.UnknownToolError`

The registry has two jobs:

1. storing tools
2. dispatching tools when asked

The agent still does not call tools directly. It emits a structured request
and the registry looks up the tool and runs it.

## Design

This step stays intentionally incremental:

- `Tool`, `Message`, and `Context` are carried forward unchanged in spirit
- `Registry.tool(...)` becomes the public tool registration API
- `Registry.dispatch(...)` performs name lookup and invokes the stored callable
- tools still remain attached to `Context.tools` in this transitional step

`Config`, `Task`, and `PLAYER` are carried forward from `01_struct_skeleton`
without changing their behavior.

## Code

| File | Purpose |
|------|---------|
| `boukensha/config.py` | `Config` class from the previous step |
| `boukensha/tasks/base.py` | `Task` dataclass from the previous step |
| `boukensha/tasks/player.py` | the `PLAYER` task |
| `boukensha/tool.py` | immutable tool definition |
| `boukensha/message.py` | immutable message record |
| `boukensha/context.py` | mutable runtime context |
| `boukensha/errors.py` | step-local Boukensha exceptions |
| `boukensha/registry.py` | tool registration and dispatch |
| `boukensha/__init__.py` | package exports |
| `prompts/system.md` | default system prompt shipped with the library |
| `examples/example.py` | runnable smoke test for this step |

## Registry API

### `Registry.tool(...)`

Registers a new tool on the context and returns the created `Tool`.

Arguments:

- `name`
- `description`
- `parameters`
- `func`

### `Registry.dispatch(name, args=None)`

Looks up a tool by name and calls it with the provided argument mapping.

If no tool is registered under that name, it raises `UnknownToolError`.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r week1_baseline/python/02_the_registry/requirements.txt
```

## Run Example

With the venv active:

```bash
./week1_baseline/python/bin/02_the_registry
```

Expected output shape:

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

## Notes

- Public registration now goes through `Registry`, not direct context calls.
- Tools still live in `Context.tools` in this step because the Ruby baseline
  keeps that intermediate design.
- Prompt resolution and config loading still behave exactly like the previous
  step.
