# Python Port Plan — 12_context

Port `week1_baseline/ruby/12_context` to
`week1_baseline/python/12_context` as the next standalone Python snapshot after
`week1_baseline/python/11_tui`.

Current starting point: the Python step-12 directory was seeded by copying the
completed Python step 11 implementation and is currently identical to it. This
plan and the implementation are delta only. Preserve the copied MCP host,
Textual front end, cooperative cancellation, loader, one-shot API, and plain
REPL behavior unless this plan explicitly changes them.

Use an iterative migration for both code and guide. Keep step 12 runnable after
each slice, document only behavior that exists, and validate each slice before
continuing:

1. add model capability lookup and context accounting primitives
2. add context compaction, token limits, configuration, and structured events
3. normalize reasoning blocks and migrate provider request/response adapters
4. expose `/compact` and context pressure in both interactive front ends
5. update package metadata and README, remove copied artifacts, and run the
   complete offline suite

This step makes context use explicit and bounded. It distinguishes the current
request size from cumulative tokens spent during a turn, automatically compacts
old messages near a model's input ceiling, adds a separate per-turn token
circuit breaker, and gives every backend one normalized reasoning-block shape.

Do not add built-in tools, change eager MCP startup, redesign the Textual app,
summarize messages during compaction, or treat cumulative token spend as the
current context size.

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/12_context/README.md` | user-facing context, compaction, limits, reasoning, provider, and TUI behavior |
| `week1_baseline/ruby/12_context/lib/boukensha/models.rb` | model-to-context-window lookup and conservative fallback |
| `week1_baseline/ruby/12_context/lib/boukensha/context.rb` | window pressure, per-turn spend, clear, and compaction primitives |
| `week1_baseline/ruby/12_context/lib/boukensha/agent.rb` | compaction timing, dual limits, usage accounting, reasoning/plan events, and wrap-up |
| `week1_baseline/ruby/12_context/lib/boukensha/config.rb` | provider/model and agent-limit defaults |
| `week1_baseline/ruby/12_context/lib/boukensha/backends/*.rb` | capability tables and normalized provider adapters |
| `week1_baseline/ruby/12_context/lib/boukensha/logger.rb` | prompt context-window, compaction, reasoning, plan, and turn token events |
| `week1_baseline/ruby/12_context/lib/boukensha/repl.rb` | `/compact` and new agent construction inputs |
| `week1_baseline/ruby/12_context/lib/boukensha/tui.rb` | true context usage, thresholds, warning marker, and compaction notices |
| `week1_baseline/ruby/12_context/lib/boukensha.rb` | assembly, overrides, snapshots, and lifecycle ownership |
| `week1_baseline/ruby/12_context/lib/boukensha/version.rb` | version `0.12.0` |

Also preserve the completed Python step 11 decisions and tests:

| File | Purpose |
|------|---------|
| `week1_baseline/python/11_tui/boukensha/run_dsl.py` | Python object assembly, configuration, MCP lifecycle, and lazy TUI import |
| `week1_baseline/python/11_tui/boukensha/tui.py` | Textual messages, worker isolation, cancellation, and headless-test seams |
| `week1_baseline/python/11_tui/boukensha/repl.py` | front-end-neutral commands/turns and injectable streams |
| `week1_baseline/python/11_tui/boukensha/agent.py` | cooperative cancellation checkpoints and bounded loop |
| `week1_baseline/python/11_tui/boukensha/logger.py` | isolated subscriber events and normalized execution metadata |
| `week1_baseline/python/11_tui/boukensha/backends/` | existing Python HTTP and provider normalization conventions |
| `week1_baseline/python/11_tui/tests/` | standard-library/offline and Textual headless regression style |

Treat unchanged copied files as already migrated. Do not import implementation
code from step 11. Remove copied or generated `build/`, `*.egg-info/`,
`__pycache__/`, `.pyc`, wheel, and source-archive artifacts before completion.

## Behavior to preserve exactly

1. Set `VERSION = "0.12.0"` and keep installed metadata derived from the runtime
   constant. Retain the distribution name, Python 3.10 minimum, dependencies,
   package inventory, and global executable from step 11.
2. Add `boukensha/models.py` with `DEFAULT_CONTEXT_WINDOW = 32_000` and a model
   lookup assembled from every backend class's `MODELS` mapping. Unknown or
   missing model identifiers use the conservative default.
3. Keep each backend's model metadata as the single source of known context
   windows. Do not copy a second hand-maintained model-size table.
4. Extend `Context` with `context_window`, `current_tokens`, `turn_tokens`, and
   `compaction_threshold`. Defaults are 200,000, 0, 0, and 0.85 respectively.
   Retain `system`, `messages`, `tools`, and normalized `working_dir`.
5. Preserve the copied optional `task` compatibility attribute where useful to
   avoid breaking the Python snapshot's public construction surface, but new
   context management must not depend on task-class settings.
6. `update_tokens(n)` stores the latest API response's input-token count;
   missing, `None`, and numeric-string values become safe integers.
7. `reset_turn_tokens()` runs at the start of every agent run.
   `add_turn_tokens(input, output)` adds one call's input and output tokens to
   the cumulative spend for that turn.
8. `usage_fraction` is `current_tokens / context_window`, or `0.0` for a
   nonpositive window. `usage_pct` is the nearest integer percentage. Do not
   silently clamp over-limit values; they remain observable.
9. `needs_compaction(threshold=None)` uses the context's configured threshold
   unless explicitly overridden and triggers when usage is greater than or
   equal to it.
10. `compact_messages(target_fraction=0.60)` drops the oldest 40 percent of
    messages, rounding upward, while keeping at least two. It resets
    `current_tokens` and returns the number dropped. Match the Ruby behavior:
    the `target_fraction` argument documents intent but does not currently
    alter the fixed 40-percent policy.
11. Clearing messages also resets `current_tokens`, but neither clear nor
    compaction removes tools, the system prompt, the working directory, model
    capacity, or per-turn configuration.
12. Add configuration accessors for `tasks.player.provider` and
    `tasks.player.model`, retaining the player defaults `anthropic` and
    `claude-haiku-4-5`.
13. Add `agent.max_iterations`, `agent.max_output_tokens`,
    `agent.max_turn_tokens`, and `agent.compaction_threshold` configuration.
    Defaults are 25, 1024, 60,000, and 0.85. Explicit `0`/`None` limit values
    disable the corresponding ceiling where the Ruby behavior says so; reject
    malformed numeric settings with useful standard conversion errors.
14. Public `run()` and `repl()` accept `context_window=None`. Resolve the model
    first, then use the explicit value or `Models.context_window(model)`.
15. Assembly constructs `Context` with the resolved window and configured
    compaction threshold. Logger snapshots include `max_iterations`,
    `max_turn_tokens`, `max_output_tokens`, `context_window`, model, and
    provider.
16. Agent construction uses the central agent configuration rather than the
    older task-level limit helpers. A public `max_output_tokens` override still
    wins over configuration.
17. Preserve `run()`/`repl()` cleanup ownership: logger and MCP clients close
    exactly once on successful completion, startup failure, model failure,
    cancellation, TUI failure, and plain-REPL exit.
18. At the start of `Agent.run()`, reset turn spend and compact once if the
    known context pressure is at or above threshold. Compaction occurs before
    the first iteration and model call.
19. Automatic compaction logs one event containing the pre-compaction token
    count, number of messages dropped, and context-window size.
20. After every successful provider call, including tool-use and wrap-up calls,
    add normalized input+output usage to `turn_tokens` and update
    `current_tokens` from normalized input tokens.
21. Reuse the backend/logger usage-normalization conventions so Anthropic,
    OpenAI, Gemini, Ollama, and Ollama Cloud accounting works. Missing usage
    must count as zero and never crash the loop.
22. Enforce `max_iterations` and `max_turn_tokens` as independent trigger
    thresholds before starting a new work iteration. A zero or negative value
    disables that threshold.
23. When the token threshold trips, emit `limit_reached` with kind
    `max_tokens`, current turn spend, and configured maximum, then perform the
    same tools-disabled terminal wrap-up used by the iteration limit.
24. The wrap-up call remains outside the iteration count. Its usage is added to
    the reported turn total, but it cannot trigger another wrap-up. Preserve
    cooperative cancellation checks around model and tool calls.
25. Every `turn_end` event includes the final cumulative turn-token count for
    normal, iteration-limited, and token-limited completion, including the
    deterministic fallback after an API error.
26. Extract multiple text blocks with newline separators, matching the Ruby
    step's readable response/plan behavior.
27. Define the normalized response contract in the backend base module. Content
    blocks are `reasoning`, `text`, or `tool_use`; reasoning precedes visible
    text/tool calls when the provider supplies that order.
28. A normalized reasoning block contains `type="reasoning"`, human-readable
    `text` (possibly empty), and optional opaque `signature`/`redacted` fields.
    Consumers never interpret provider signatures.
29. Emit one logger `reasoning` event for each reasoning block. Skip empty
    non-redacted blocks, but log redacted/omitted reasoning so its existence is
    visible.
30. For a tool-use response, log nonblank accompanying text as a separate
    `plan` event, then log the deterministic `(tool use — N call[s])` response
    placeholder with the call's usage. Do not double-charge usage to the plan.
31. Extend `Logger.prompt` with `context_window`; add `compaction`, `reasoning`,
    and `plan` methods. Preserve write-before-publish order and subscriber-copy
    isolation from step 11.
32. Anthropic maps native `thinking` and `redacted_thinking` to reasoning
    blocks and reverses that mapping for assistant-history requests, preserving
    opaque signatures/data exactly.
33. Gemini maps `thought`/`thoughtSignature`, preserves signatures on reasoning
    and function-call parts, and sends thinking disabled for the supported
    models (`thinkingBudget: 0`; use the model-specific level form where
    required).
34. Ollama and Ollama Cloud send `think: false`, normalize any returned
    `message.thinking`, and omit reasoning blocks when rebuilding assistant
    history because their request format does not need them.
35. Migrate OpenAI from Chat Completions to `/v1/responses`: system prompt to
    `instructions`, conversation to `input`, flat function definitions,
    `function_call`/`function_call_output` round-tripping by `call_id`,
    `max_output_tokens`, and `reasoning: {effort: "none"}`.
36. OpenAI response parsing reads `output[]`, normalizes reasoning summaries,
    output text, and function calls, and safely parses absent or malformed-empty
    argument strings as an object. Assistant history drops reasoning blocks.
37. Keep backend model tables aligned with Ruby step 12, including OpenAI's
    Responses-compatible model set and all context-window/cost metadata.
38. Add `/compact` to plain REPL and TUI help. It compacts immediately and
    outputs `(compacted context — N messages dropped)` without ending the
    session or clearing registered tools.
39. The TUI derives idle and status context use from `Context.current_tokens`
    and `Context.context_window`, never from cumulative session usage. It shows
    `used / max (pct%)` in the idle progress line and `used/max (pct%)` in the
    status bar.
40. TUI context state is normal below 70 percent, warning from 70 through 84
    percent, and alert at 85 percent or above. Add a textual warning marker at
    alert level so meaning is not conveyed by color alone.
41. A `compaction` subscriber event appends
    `[context compacted — N messages dropped to free space]` to the
    conversation. Worker callbacks continue to post immutable messages; only
    the Textual application thread mutates widgets.
42. Preserve all step-11 turn ids, stale-event rejection, scrolling behavior,
    worker completion ordering, cooperative interruption, and shutdown waits.
43. Keep `run()` importable and usable without Textual. TUI remains the default
    only for interactive `repl()`; `--no-tui` behavior is unchanged.
44. Preserve MCP wire behavior. Python does not need Ruby Bundler environment
    cleanup; retain the existing subprocess environment isolation and useful
    stderr/startup errors rather than porting `Bundler.with_unbundled_env`.
45. Update README examples and comments to step 12, document the distinction
    between context pressure and turn spend, configuration defaults,
    auto/manual compaction, reasoning normalization, provider caveats, TUI
    thresholds, build/install commands, and offline tests.
46. Prior Python snapshots and repository-wide configuration remain unchanged.
    Do not add Ruby gem artifacts, Charm patches, Ruby-only uninstall advice,
    absolute developer paths, or claims that Python uses Bubble Tea.

## Python-specific decisions

- Represent model metadata with ordinary immutable-by-convention class mappings
  and build `models.py` lazily or after backend imports to avoid circular imports.
- Add a shared, defensive usage-normalization helper only if it reduces drift
  between logging and context accounting. Keep provider wire adapters responsible
  for translating provider fields into the existing normalized metadata.
- Use `math.ceil` for compaction count and list slicing for deterministic oldest-
  first removal. Do not mutate retained `Message` objects.
- Keep numeric conversion explicit. A small helper may treat `None` as zero for
  response usage while configuration continues to surface invalid values.
- Preserve snake_case Python APIs: `compact_messages`, `needs_compaction`, and
  property accessors rather than Ruby punctuation naming.
- Keep pure TUI helpers for token formatting, context severity, progress text,
  and status text independently testable without a terminal or wall-clock sleep.
- Extend existing fake backends/clients and JSONL tests. All provider tests use
  captured mappings; no test may call a live API, MCP service, or model.
- Continue using `unittest` and Textual's headless pilot support already present
  in step 11. Test both plain REPL and TUI command routing.

## Required validation

Add or update offline tests covering:

- known/unknown model-window lookup and all context calculations
- compaction rounding, two-message floor, reset behavior, and threshold edges
- agent auto-compaction ordering, per-call accounting, both limits, wrap-up
  accounting/fallback, cancellation, reasoning, and plan events
- config defaults, explicit values, and assembly snapshots/overrides
- every provider's reasoning normalization and assistant-history round trip
- OpenAI Responses request and response shapes
- logger event payloads and subscriber isolation
- plain `/compact`, TUI compaction notices, context formatting/severity, and
  retention of all step-11 input/cancellation/shutdown behavior
- complete step-12 test discovery plus an artifact scan

## Proposed target layout

```text
week1_baseline/python/12_context/
  pyproject.toml                  # v0.12.0; retained dependencies
  requirements.txt               # unchanged runtime dependency set
  README.md                       # Python context-management guide
  boukensha_cli.py                # retained --no-tui boundary
  boukensha_loader.py             # retained implementation/config selection
  boukensha/
    models.py                     # model capability lookup
    context.py                    # context pressure, turn spend, compaction
    agent.py                      # dual limits, accounting, reasoning events
    config.py                     # provider/model and agent settings
    logger.py                     # context/reasoning/compaction events
    repl.py                       # /compact and configured limits
    tui.py                        # context pressure display and notices
    run_dsl.py                    # context_window assembly and snapshots
    backends/
      base.py                     # normalized content-block contract
      anthropic.py                # signed thinking round trip
      openai.py                   # Responses API adapter
      gemini.py                   # thought/signature normalization
      ollama.py                   # thinking normalization
      ollama_cloud.py             # thinking normalization
    version.py                    # VERSION = "0.12.0"
  tests/                          # expanded offline regression suite
```
