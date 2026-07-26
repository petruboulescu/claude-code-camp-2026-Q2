# Step 6 — The Logger

`boukensha.Logger` records each agent run as structured JSON Lines. It is a
file logger, not user-facing display output.

## Session logs

Each `Logger` instance creates a session ID and writes one file for that
session:

```text
.boukensha/sessions/<session-id>.jsonl
```

Every line is a complete JSON object with `session_id`, `at`, and `phase`
fields, plus phase-specific data. That makes logs friendly to `grep`, `tail`,
and machine readers.

```json
{"phase":"session_start","session_id":"20260528T143011Z-a1b2c3d4","at":"2026-05-28T10:30:11-04:00"}
{"phase":"iteration","n":1,"max":25,"session_id":"20260528T143011Z-a1b2c3d4","at":"2026-05-28T10:30:11-04:00"}
```

Model response lines include the active task, provider, model, normalized
token counts, and estimated USD cost when the backend has token pricing data:

```json
{"phase":"response","task":"player","provider":"anthropic","model":"claude-haiku-4-5","input_tokens":1000,"output_tokens":100,"cost_usd":0.0015}
```

## Logger API

The logger is a plain object with one method per phase:

| Method | Phase | Logs |
|---|---|---|
| `iteration(n=, max=)` | `iteration` | loop counter and threshold |
| `limit_reached(kind=, n=, max=)` | `limit_reached` | the threshold that stopped new work |
| `turn_end(reason=, iterations=)` | `turn_end` | terminal reason and iteration count |
| `prompt(messages=, tools=)` | `prompt` | messages and registered tools |
| `tool_call(name=, args=)` | `tool_call` | tool name and arguments |
| `tool_result(name=, result=)` | `tool_result` | tool result or recovered error |
| `response(text=, usage=, task=, backend=)` | `response` | text, usage, execution metadata, and estimated cost |
| `raw(data=)` | `raw` | raw provider response when debug is enabled |

## Task configuration

Step 6 keeps the task-based settings shape:

```yaml
tasks:
  player:
    provider: anthropic
    model: claude-haiku-4-5
    prompt_override:
      system: true
```

When `prompt_override.system` is true, the player task reads
`.boukensha/prompts/player/system.md`. Otherwise it falls back to this step's
shipped `prompts/system.md`.

Default usage:

```python
from boukensha import Agent, Logger

logger = Logger()
agent = Agent(
    context=ctx,
    registry=registry,
    builder=builder,
    client=client,
    logger=logger,
)
```

You can provide a session ID or override the destination directory:

```python
Logger(session_id="manual-session")
Logger(dir="/tmp/boukensha-sessions")
```

For compatibility, `log=` accepts an explicit file path, but normal agent
usage should write under `.boukensha/sessions`.

The agent now records ordinary tool failures as failed `tool_result` events
and sends an `ERROR: ...` tool-result message back to the model. This lets the
model explain or recover from a failed action without losing the structured
trace.

## Debug events

Call `debug()` before running the agent to include full raw provider responses:

```python
from boukensha import debug

debug()
```

Raw responses can contain sensitive prompt or provider data, so they are
disabled by default.

Close the logger when the session is no longer needed:

```python
logger.close()
```

## Run the example

```sh
./week1_baseline/python/bin/06_the_logger
```
