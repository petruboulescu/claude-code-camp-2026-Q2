# Step 11 — A Terminal UI

Boukensha now starts a full-screen terminal UI built with
[Textual](https://textual.textualize.io/). The plain step-10 REPL remains
available with `--no-tui` or `boukensha.repl(tui=False)`. MCP still supplies
all automatic tools; this step changes presentation, not capabilities.

## Iteration 1: a composable session

`Repl` still owns conversation history, slash commands, turn numbering, and
agent construction, but no longer requires its own input loop. Front ends use
`on_output(callback)`, `banner()`, `handle_command(text)`, and
`run_turn(text, cancel_event=None)`. The ordinary `start()` loop is preserved
for scripts, redirected streams, and terminals where a full-screen application
is undesirable.

## Iteration 2: progress and cancellation

Every JSONL logger event is also delivered to subscribers after it is flushed.
The TUI consumes iteration, tool-call, tool-result, and response events without
polling the file.

Escape cancellation is cooperative. Boukensha checks a `threading.Event` at
agent-loop boundaries and before and after provider and tool calls. Python
cannot safely inject an exception into another thread, so an already-blocking
network or tool call must finish before cancellation takes effect.

## Iteration 3: four-zone display

```text
┌──────────────────────────────────────────────┐
│ conversation (scrollable)                    │
├──────────────────────────────────────────────┤
│ ⟳ action · iteration · time · tokens · calls│
├──────────────────────────────────────────────┤
│ Type a message…                              │
├──────────────────────────────────────────────┤
│ version · model · context · tools · clock   │
└──────────────────────────────────────────────┘
```

Active progress shows the current action, effective iteration limit, elapsed
seconds, per-turn input/output tokens, and tool calls. Idle progress shows
cumulative input-token usage (a context proxy) and completed turns. The status
line always shows version, model, cumulative usage, registered tools, and time.

## Iteration 4: interaction

| Key | Action |
|---|---|
| `Enter` | Submit text or a slash command. |
| `Esc` | Request interruption of the active turn. |
| `Ctrl+L` | Clear conversation history. |
| `PgUp` / `PgDn` | Scroll conversation output. |
| `Ctrl+C` / `Ctrl+D` | Quit after an active turn cancels safely. |

Agent work runs in a worker thread. Callbacks post messages back to Textual;
only the application thread changes widgets. A second turn cannot start while
one is active. Existing `/help`, `/quiet`, `/loud`, `/clear`, `/exit`, and
`/quit` behavior is unchanged.

## Iteration 5: install and run

```bash
cd week1_baseline/python/11_tui
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --force-reinstall .

boukensha             # Textual TUI (default)
boukensha --no-tui    # plain blocking REPL
```

Programmatically, call `boukensha.repl()` for the TUI or
`boukensha.repl(tui=False)` for the plain interface. The examples remain
non-TUI demonstrations: `example.py` is a one-shot run and `mcp_demo.py` is an
offline stdio MCP smoke test.

Run all offline tests with:

```bash
python -m unittest discover -s tests -v
```

## MCP configuration

Capabilities still come from `settings.yaml`:

```yaml
mcp_servers:
  mud:
    command: mud-manager
    args: [--mcp]
    prefix: tbamud
    env:
      MUD_HOST: your.mud.host
    required: true
```

| Key | Default | Meaning |
|---|---|---|
| `command` | — | Executable spawned directly without a shell. |
| `args` | `[]` | Server argument vector. |
| `env` | `{}` | Environment overrides inherited by the server. |
| `prefix` | none | Local namespace such as `tbamud__look`. |
| `required` | `true` | Optional failures warn; required failures abort startup. |

Servers connect eagerly, collisions are fatal, and `working_dir` remains
context metadata rather than a capability or server root.

## Technical considerations

- A blocking provider or tool call delays cooperative interruption.
- Servers spawn eagerly even if the model never calls their tools.
- Non-text MCP content blocks are currently ignored.
- Backend schemas still advertise every listed parameter as required.
- Cumulative input tokens are a context proxy, not an exact remaining-window
  measurement.
