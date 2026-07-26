# Step 7 — The `boukensha.run` DSL

`boukensha.run()` is the concise entry point for one player-agent turn. It
resolves configuration, builds the agent stack, registers tools, runs the
bounded loop, and closes the session logger.

## The DSL

Python uses a setup callback and decorators in place of Ruby's block DSL:

```python
from pathlib import Path

import boukensha

base_dir = Path.cwd()

def configure(dsl):
    @dsl.tool(
        "read_file",
        description="Read a UTF-8 file",
        parameters={"path": {"type": "string"}},
    )
    def read_file(path):
        return (base_dir / path).read_text(encoding="utf-8")

result = boukensha.run(
    task="Summarize README.md",
    configure=configure,
)
```

`RunDSL` deliberately exposes tool registration only. Existing primitives
remain public for callers that need manual wiring.

## Options

| Option | Default | Description |
|---|---|---|
| `task` | required | User message handed to the player agent |
| `system` | player task prompt | System prompt override |
| `model` | player task model | Model override |
| `backend` | player task provider | `anthropic`, `openai`, `gemini`, `ollama`, or `ollama_cloud` |
| `api_key` | provider environment variable | API key override; unused by local Ollama |
| `ollama_host` | `http://localhost:11434` | Local Ollama base URL |
| `log` | generated session path | Explicit JSONL path |
| `max_output_tokens` | player task setting | Per-response output limit |
| `configure` | `None` | Callback receiving the `RunDSL` |

The runner loads `.boukensha/.env` before resolving a default API key. The
provider variables are `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
`GEMINI_API_KEY`, and `OLLAMA_API_KEY`.

## Direct tool registration

A setup callback may register an existing callable without decorator syntax:

```python
def configure(dsl):
    dsl.tool(
        "lookup",
        description="Look up a value",
        func=lookup,
    )
```

## Session logs

Every run owns one `Logger`, normally writing to:

```text
.boukensha/sessions/<session-id>.jsonl
```

The `session_start` event records the resolved task, provider, model, and
limits. All step-6 prompt, response, usage, tool, limit, and terminal events
remain unchanged.

`Logger.subscribe(callback)` observes later phase events synchronously after
each JSONL line is flushed. `Logger.turn(n=...)` is also available for clients
that need an explicit turn marker.

```python
logger.subscribe(handle_event)
logger.turn(n=1)
```

Subscribers do not receive the logger-added `session_id` or timestamp. A
runner-owned logger is always closed, including when execution raises.

Raw provider events remain debug gated:

```python
boukensha.debug()
```

## Run the example

```sh
./week1_baseline/python/bin/07_the_run_dsl
```
