# Step 12 — Context Management (Python)

This snapshot adds explicit context-window management to the MCP-host agent and
Textual interface from step 11. Boukensha still ships no built-in tools: tools
come from the MCP servers configured in `settings.yaml`.

## Build and install

```sh
python -m build
python -m pip install dist/boukensha-0.12.0-py3-none-any.whl
```

The runtime dependencies are PyYAML, python-dotenv, and Textual. The plain REPL
and one-shot API remain independent of Textual at import time.

## Context pressure and turn spend

The two token counters answer different questions:

| Value | Meaning |
|-------|---------|
| `context_window` | Maximum model input capacity, resolved from model metadata |
| `current_tokens` | Input tokens reported by the most recent provider call |
| `turn_tokens` | Cumulative input plus output tokens spent in the current turn |

`current_tokens / context_window` determines compaction pressure. It is not a
cumulative session bill. `turn_tokens` is reset for each agent turn and drives
the independent per-turn spending circuit breaker.

Known model sizes come from each backend's `MODELS` mapping. Unknown models use
a conservative 32,000-token fallback:

```python
from boukensha.models import Models

Models.context_window("gpt-5.5")   # 1_000_000
Models.context_window("custom")    # 32_000
```

`run()` and `repl()` accept an explicit override when required:

```python
import boukensha

boukensha.repl(context_window=128_000)
```

## Automatic and manual compaction

Before a turn's first model call, the agent checks context pressure. At or above
`agent.compaction_threshold` (0.85 by default), it drops the oldest 40 percent
of messages while retaining at least two. It then resets `current_tokens`; the
next provider response supplies the new measured input size.

The operation is deliberately mechanical in this teaching snapshot: it does
not summarize discarded messages. Tools, system prompt, model capacity, and MCP
connections are retained.

Run the same operation manually from either front end:

```text
boukensha> /compact
(compacted context — 12 messages dropped)
```

Automatic compaction also emits a structured event and a TUI notice:

```json
{"phase":"compaction","before":172000,"dropped":12,"context_window":200000}
```

```text
[context compacted — 12 messages dropped to free space]
```

`/clear` still removes all conversation messages and now also resets measured
context use. Neither command removes registered tools.

## Agent limits

Configure the two independent turn limits and the per-call output limit in
`settings.yaml`:

```yaml
agent:
  max_iterations: 25
  max_output_tokens: 1024
  max_turn_tokens: 60000
  compaction_threshold: 0.85
```

The agent checks iteration and token thresholds before starting new work. When
either trips, it performs one final tools-disabled wrap-up call. That call does
not increment iterations, but its tokens are included in the final turn total.
A zero/negative turn or iteration limit disables that threshold.

## Normalized reasoning blocks

Every backend returns the same content-block contract from `parse_response()`:

```python
{
    "stop_reason": "tool_use",  # or "end_turn"
    "content": [
        {"type": "reasoning", "text": "...", "signature": "opaque"},
        {"type": "text", "text": "..."},
        {"type": "tool_use", "id": "...", "name": "look", "input": {}},
    ],
}
```

Reasoning signatures are opaque transport data. Anthropic thinking and
redacted-thinking blocks are reconstructed exactly for history; Gemini thought
signatures are carried on thought/function-call parts. Ollama and Ollama Cloud
normalize returned `thinking` but request thinking disabled. Logger
`reasoning` and `plan` events make thinking and tool preambles independently
observable without charging response usage twice.

The OpenAI adapter now uses `/v1/responses`: the system prompt is
`instructions`, conversation messages become `input` items, function tools are
flat, and tool results use `function_call_output` matched by `call_id`.

## Terminal interfaces

Running `boukensha` launches the four-zone Textual UI:

```text
conversation viewport
live/ready progress
single-line input
status bar
```

From a repository checkout, launch this final snapshot's full TUI directly:

```sh
week1_baseline/python/bin/12_context
```

The launcher works from any current directory, pins implementation loading to
`python/12_context`, and preserves your normal `BOUKENSHA_DIR`, provider, and
API-key environment variables. Any arguments are forwarded to the global CLI.

The idle and status lines show measured context use against the model maximum.
Below 70% is normal, 70–84% is warning, and 85%+ is alert. Alert state includes
a `⚠` marker, so it remains understandable without color.

| Key | Action |
|-----|--------|
| `Enter` | Submit input or a slash command |
| `Esc` | Request cooperative interruption of a running turn |
| `Ctrl+L` | Clear conversation history |
| `PgUp` / `PgDn` | Scroll the conversation |
| `Ctrl+C` / `Ctrl+D` | Quit after the active worker finishes |

Use the retained plain terminal interface with:

```sh
boukensha --no-tui
```

or programmatically:

```python
boukensha.repl(tui=False)
```

Cooperative cancellation cannot preempt a provider or MCP tool blocked inside
third-party code; cancellation is observed at the next loop/call boundary.

## MCP configuration

```yaml
mcp_servers:
  filesystem:
    command: npx
    args: [-y, "@modelcontextprotocol/server-filesystem", /tmp]
    prefix: fs
    required: false
```

Servers start eagerly. `command`, `args`, and `env` use the standard stdio
transport; `prefix` prevents tool-name collisions; `required: false` converts a
startup failure into a warning. Server reconnection, remote transports, and
runtime MCP reconfiguration remain outside this snapshot.

## Examples and tests

The examples are one-shot/MCP examples; the TUI is launched through the global
executable.

```sh
python examples/example.py
python examples/mcp_demo.py --dry
python -m unittest discover -s tests -v
```

All tests are offline. Provider adapters are tested with captured dictionaries,
and the TUI uses Textual's headless pilot support when Textual is installed.
