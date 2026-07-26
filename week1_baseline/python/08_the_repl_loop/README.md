# Step 8 — The REPL Loop

`boukensha.repl()` adds an interactive, multi-turn session alongside the
one-shot `boukensha.run()` entry point from step 7. Tools and provider objects
are built once, while conversation history accumulates across prompts.

## Start a session

Python uses the same setup callback and decorator DSL as step 7:

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


boukensha.repl(configure=configure)
```

The options match `boukensha.run()` except there is no `task`; each task is
read interactively.

| Option | Default |
|---|---|
| `system` | player task prompt |
| `model` | player task model |
| `backend` | player task provider |
| `api_key` | matching provider environment variable |
| `ollama_host` | `http://localhost:11434` |
| `log` | generated session JSONL path |
| `max_output_tokens` | player task setting |
| `configure` | `None` |

Supported backends are `anthropic`, `openai`, `gemini`, `ollama`, and
`ollama_cloud`.

## Commands

| Command | Effect |
|---|---|
| `/help` | Show the command list |
| `/quiet` | Enable the existing quiet runtime mode |
| `/loud` | Disable quiet runtime mode |
| `/clear` | Clear conversation history while retaining tools |
| `/exit`, `/quit` | End the session |
| Ctrl-D | End the session at end-of-file |
| Ctrl-C | Interrupt the session gracefully |

Commands are handled locally and are never sent to the model. Final answers
are always printed. The session's JSONL file remains the durable detailed log.

## Persistent history

Each user prompt gets a fresh `Agent`, resetting the per-turn action budget.
All agents share the same `Context`, so user messages, tool calls, tool
results, and final assistant replies remain visible on later turns.

`/clear` empties only that transcript. The system prompt and registered tools
stay active.

## Configuration

The configuration directory is selected in this order:

1. `BOUKENSHA_DIR`
2. an existing `.boukensha` directory in the current working directory
3. `~/.boukensha`

The configuration is cached for the process. Its `.env` file supplies
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, or
`OLLAMA_API_KEY`. Local Ollama requires no key.

## Run the example

```sh
./week1_baseline/python/bin/08_the_repl_loop
```
