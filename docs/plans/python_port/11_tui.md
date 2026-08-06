# Python Port Plan — 11_tui

Port `week1_baseline/ruby/11_tui` to
`week1_baseline/python/11_tui` as the next standalone Python snapshot after
`week1_baseline/python/10_standard_tools`.

Current starting point: the Python step-11 directory was seeded by copying the
completed Python step 10 implementation and is currently identical to it. This
plan and the implementation are delta only. Keep the copied MCP host, backend,
agent, loader, logging, and one-shot behavior unless this plan explicitly
changes them.

Use an iterative migration for both the code and its guide. Keep the copied
plain REPL runnable until the TUI is complete, add one independently testable
UI seam at a time, document only behavior that exists, and validate each slice
before proceeding:

1. refactor `Repl` into a front-end-neutral session controller
2. add deterministic progress events and cooperative turn cancellation
3. build and test the static Textual layout and rendering helpers
4. connect input, background turns, progress updates, scrolling, and shortcuts
5. make the TUI the default, retain `--no-tui`, replace the copied guide, and
   run the full offline suite

This step adds a full-screen terminal front end without changing what the agent
can do:

- show a scrollable conversation, live progress, input box, and status bar
- keep the interface responsive while an agent turn runs in a worker thread
- display iterations, elapsed time, token usage, tool calls, context usage,
  model, version, registered tool count, and wall-clock time
- submit text and slash commands from the same input widget
- interrupt a turn with `Esc`, clear with `Ctrl+L`, scroll with Page Up/Down,
  and quit with `Ctrl+C` or `Ctrl+D`
- launch the TUI by default and retain the copied REPL with `--no-tui`
- preserve MCP startup/cleanup and all noninteractive `run()` behavior

Do not redesign the agent loop, add new tools, change MCP protocol behavior,
replace JSONL logging, or turn the TUI into a general GUI framework lesson.

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/11_tui/README.md` | four-zone UI, shortcuts, default/fallback startup, demo, and limitations |
| `week1_baseline/ruby/11_tui/lib/boukensha/tui.rb` | model state, rendering, event queue, background turns, keys, and progress accounting |
| `week1_baseline/ruby/11_tui/lib/boukensha/repl.rb` | output callback, public command/turn seams, and front-end-neutral session behavior |
| `week1_baseline/ruby/11_tui/lib/boukensha/logger.rb` | structured-event subscriptions used by live progress |
| `week1_baseline/ruby/11_tui/lib/boukensha.rb` | `tui:` option, default selection, object assembly, and cleanup ownership |
| `week1_baseline/ruby/11_tui/lib/boukensha_loader.rb` | `--no-tui` consumption and forwarding |
| `week1_baseline/ruby/11_tui/bin/boukensha` | global executable surface |
| `week1_baseline/ruby/11_tui/lib/boukensha/version.rb` | version `0.11.1` |
| `week1_baseline/ruby/11_tui/boukensha.gemspec` and `Gemfile` | Charm dependency intent |
| `week1_baseline/ruby/11_tui/patches/bubbletea/` | upstream input-loss issue and why the Ruby port loads only required Charm components |
| `week1_baseline/ruby/11_tui/examples/` | unchanged one-shot/MCP demos and clarification that the TUI is launched globally |

Also preserve the completed Python step 10 decisions and tests:

| File | Purpose |
|------|---------|
| `week1_baseline/python/10_standard_tools/boukensha/run_dsl.py` | Python assembly order, MCP lifecycle, and `run()`/`repl()` ownership |
| `week1_baseline/python/10_standard_tools/boukensha/repl.py` | injectable-stream plain REPL and persistent session behavior |
| `week1_baseline/python/10_standard_tools/boukensha/logger.py` | existing callback subscription and normalized usage events |
| `week1_baseline/python/10_standard_tools/boukensha/agent.py` | iteration boundaries, task limits, and tool dispatch |
| `week1_baseline/python/10_standard_tools/boukensha/context.py` | messages and registered-tool count |
| `week1_baseline/python/10_standard_tools/boukensha_loader.py` | implementation/config selection and rc compatibility |
| `week1_baseline/python/10_standard_tools/boukensha_cli.py` | injectable global entry point |
| `week1_baseline/python/10_standard_tools/pyproject.toml` | setuptools metadata and package inventory |
| `week1_baseline/python/10_standard_tools/tests/` | standard-library-only offline regression style |

Treat unchanged copied files as already migrated. Do not import implementation
code from step 10. Remove copied or generated `build/`, `*.egg-info/`,
`__pycache__/`, `.pyc`, wheel, and source-archive artifacts before completion.

## Behavior to preserve exactly

1. Set `VERSION = "0.11.1"` and continue deriving installed package metadata
   from the runtime constant.
2. Keep the distribution name `boukensha`, Python 3.10 minimum, global
   `boukensha` script, `pyyaml`, and `python-dotenv`. Add `textual` as the one
   step-11 UI dependency; do not add Rich separately because Textual supplies
   and constrains it.
3. Add `boukensha/tui.py` with a `Tui` front end around one already-assembled
   `Repl`. `Tui` must not construct its own backend, registry, logger, context,
   or MCP clients.
4. Preserve four visible zones, top to bottom: a scrollable conversation
   viewport, one progress line, one single-line input, and an always-visible
   status line. Resize them with the terminal and give the conversation the
   remaining vertical space.
5. Seed the conversation with the ordinary REPL banner. Append submitted user
   text as `> <text>` and route every REPL response/error/command message into
   the same conversation instead of stdout.
6. Keep the conversation pinned to the newest output when new content arrives,
   while Page Up and Page Down scroll by a small stable amount. Do not reset
   user scroll merely because the clock/spinner refreshes.
7. The idle progress line reports ready state, cumulative input/context-token
   usage, and completed turn count. The active line reports a spinner, current
   action, `iteration/max`, whole elapsed seconds, current-turn input/output
   tokens, and tool-call count.
8. Use the configured/effective maximum iteration value for `iteration/max`;
   do not hard-code the class default when settings or a caller override it.
9. The status line always reports Boukensha version, effective model,
   cumulative context/input-token usage, `Context.tool_count`, and current
   local wall-clock time. Render a sensible fallback when the model is absent.
10. Format token counts below 1,000 as integers and counts at or above 1,000 as
    one-decimal `k` values, matching the Ruby display intent.
11. Keep styles semantic and modest: highlighted prompt, subdued ready line,
    cyan live progress, and contrasting status bar. The interface must remain
    understandable in monochrome/no-color terminals; state cannot be conveyed
    by color alone.
12. `Enter` trims and submits nonblank input. Slash-prefixed input goes through
    `Repl.handle_command`; ordinary input starts an agent turn. Clear the input
    immediately after accepting either.
13. Do not start a second turn while one is active. Disable submission or leave
    the entered text intact with a visible busy indication rather than racing
    two agents against the shared context and logger.
14. `Esc` requests cancellation of the active turn. Python cannot safely inject
    an exception into another thread as Ruby's `Thread#raise` does, so implement
    a per-turn `threading.Event` checked before and after model calls and tool
    calls and at every agent-loop boundary. A blocking provider or tool call may
    finish before cancellation is observed; document this honest limitation.
15. Cancellation produces one `[interrupted]` conversation entry, does not
    print an ordinary final answer, ends active progress, and leaves the session
    usable for another turn. Pressing `Esc` while idle is a no-op.
16. `Ctrl+L` invokes the same `/clear` behavior as the plain REPL, resets the
    displayed conversation to a concise cleared-state message/banner, resets
    the REPL and TUI turn counters, and does not remove registered tools or stop
    MCP servers.
17. Page Up/Page Down scroll the conversation. `Ctrl+C` and `Ctrl+D` request UI
    exit. If a turn is active, request cancellation and wait for the worker to
    finish before returning control to the outer MCP/logger cleanup.
18. Keep slash-command behavior and text exactly aligned between front ends:
    `/exit`, `/quit`, `/help`, `/quiet`, `/loud`, and `/clear` retain their
    step-10 meanings. A quit command exits the TUI through its normal shutdown
    path.
19. Refactor `Repl` to expose read-only session data needed by the UI
    (`logger`, `context`, `model`, `version`, and effective max iterations),
    `banner()`, `on_output(callback)`, `handle_command(input)`, and
    `run_turn(input, cancel_event=None)`.
20. `handle_command` returns an explicit three-way result (`quit`, `command`,
    or `not_command`) rather than overloading a boolean whose old meaning mixed
    quitting with running an ordinary turn. Keep the result internal or use a
    small enum; do not make callers compare Ruby symbols.
21. `Repl.start()` remains the plain blocking loop. It uses the new public
    seams, writes the prompt only when no output callback owns presentation,
    skips blank input, stops on EOF, and preserves injected input/output streams
    for tests and embedding.
22. All `Repl` output goes through one method. With an output callback set, do
    not also print to its configured stream. Without a callback, preserve the
    copied plain-REPL transcript, including final responses and concise
    `LoopError`/`ApiError` messages.
23. Keep the logger's existing `subscribe(callback)` behavior: write and flush
    the JSONL event first, then send an event without session/timestamp envelope
    fields to a snapshot of subscribers. One subscriber modifying the mapping
    must not corrupt the file or another subscriber's event.
24. Do not update Textual widgets from the worker thread. Logger/output
    callbacks enqueue or post immutable UI messages; the Textual application
    thread alone mutates widgets and presentation state.
25. Interpret `iteration`, `tool_call`, `tool_result`, and `response` events as
    Ruby does: Thinking, Calling tool, Awaiting result, and usage accumulation.
    Accept missing/`None` usage and provider-specific normalized usage without
    crashing the UI.
26. Count every `tool_call` event. Accumulate input and output tokens per turn
    and per session, but display cumulative input tokens as the context proxy,
    matching the Ruby source; do not claim this is an exact provider context
    window measurement.
27. Always post a turn-complete event from a worker `finally` block. Convert an
    unexpected worker exception into one `[error] <message>` entry, reset the
    active state exactly once, and keep the Textual event loop alive.
28. Ensure worker completion ordering cannot erase an interrupt/error or mark
    the next turn complete. Give each turn an id and ignore stale progress and
    completion messages from an older turn.
29. Add `tui=True` to the public `repl()` API. Assemble the ordinary `Repl`
    first; when true construct and start `Tui`, and when false call
    `Repl.start()` directly.
30. Import the optional UI on the TUI path rather than at package import time.
    The plain REPL, one-shot API, loader inspection, and MCP tests must remain
    importable when Textual is unavailable. If TUI startup is requested without
    Textual, raise a concise error that recommends installing the step's normal
    dependencies or using `--no-tui`; do not silently change front ends.
31. Preserve the outer `repl()` ownership and `finally` blocks. Normal exit,
    startup failure, widget failure, worker error, cancellation, and plain-REPL
    fallback must close the logger and all connected MCP clients exactly once
    and in the existing order.
32. Parse only `--no-tui` at the global boundary, remove it from the argument
    list passed through loader seams, and call the selected implementation's
    `repl(tui=False)`. With no flag, call `repl(tui=True)`.
33. Preserve step-10 loader rules: environment overrides, YAML and bare-path rc
    formats, relative path resolution, development-package replacement,
    config-before-import ordering, and useful errors. Do not reimplement
    argument parsing inside the selected package.
34. The CLI must accept injectable argv/stdout/stderr in tests. Unknown
    arguments retain the Ruby executable's ignored-argument behavior; only
    `--no-tui` has meaning in this step.
35. Keep `run()` noninteractive and completely independent of Textual. The
    existing Python examples remain one-shot and offline MCP examples; update
    their step labels/comments only and do not pretend they demonstrate a TUI.
36. Replace the copied README incrementally with a Python step-11 guide. Show
    build/install commands, the four-zone layout, progress/status contents, all
    shortcuts, default TUI launch, `--no-tui`, programmatic `repl(tui=False)`,
    and how the Repl/logger seams support alternative front ends.
37. Retain the Ruby README's current MCP limitations and add the cooperative
    cancellation limitation. Do not carry Ruby-only gem uninstall advice,
    absolute developer paths, Charm patch instructions, or claims that Python
    uses Bubble Tea.
38. Prior Python snapshots and repository-wide configuration remain unchanged.
    Do not add shell/filesystem/MUD tools, change MCP eager startup, or fix
    unrelated technical considerations in this snapshot.

## Python-specific decisions

- Use Textual for the full-screen UI. Map the Ruby viewport, textarea, spinner,
  and Lip Gloss styling to a `RichLog` (or equivalent scrollable widget),
  single-line `Input`, reactive/static progress and status widgets, bindings,
  and CSS contained in `boukensha/tui.py`. Do not port Bubble Tea's model API or
  the Ruby C patch.
- Keep the UI logic in a small application class and pure helpers/state objects
  where practical. Token formatting, event reduction, status/progress text,
  and command routing should be testable without a real terminal.
- Use Textual's worker/message mechanisms plus `threading.Event`; never call
  `asyncio.run()` inside the app and never mutate shared widget state directly
  from the agent thread.
- Add a dedicated internal cancellation exception (for example
  `TurnCancelled`) and thread the optional cancellation check through `Repl`
  and `Agent`. Catch it at the front-end boundary, not as an API or loop error.
- Check cancellation around backend calls and registry dispatch without
  changing backend/tool signatures. This provides safe cooperative semantics
  but cannot preempt blocking third-party code.
- Use monotonic time for elapsed duration and local `datetime` only for the
  displayed clock. Tests inject or isolate time-dependent formatting rather
  than sleeping.
- Prefer Textual's headless application test support for keys, resize, widget
  state, and worker messages. Keep tests offline and avoid snapshots containing
  ANSI sequences, terminal-dependent widths, or wall-clock values.
- Test the plain REPL independently with `StringIO` so installing a UI library
  does not weaken existing embedding behavior.
- Update `requirements.txt` consistently with `pyproject.toml`, and keep
  setuptools' existing package/module inventory; `boukensha/tui.py` is included
  automatically as part of the `boukensha` package.
- Test missing-Textual behavior by controlling the import seam, not by
  uninstalling packages or modifying the environment.
- Do not use `ctypes`, CPython thread-state APIs, signals aimed at worker
  threads, or daemon-thread abandonment to imitate Ruby `Thread#raise`.

## Proposed target layout

```text
week1_baseline/python/11_tui/
  pyproject.toml                  # v0.11.1 and Textual dependency
  requirements.txt               # matching runtime dependencies
  README.md                       # iterative Python TUI guide
  boukensha_cli.py                # forwards argv to loader seam
  boukensha_loader.py             # --no-tui plus retained selection rules
  boukensha/
    tui.py                        # Textual app, widgets, state, messages, keys
    repl.py                       # composable session/front-end methods
    agent.py                      # cooperative cancellation checkpoints
    logger.py                     # retained tested event subscriptions
    run_dsl.py                    # tui=True selection and lifecycle ownership
    version.py                    # VERSION = "0.11.1"
    ...                           # unchanged step-10 MCP host and backends
  examples/
    example.py                    # unchanged one-shot intent, step-11 comments
    mcp_demo.py                   # unchanged offline MCP smoke intent
  tests/
    test_tui.py                   # reducer/rendering and headless interaction
    test_repl.py                  # public seams plus plain fallback regressions
    test_agent.py                 # cancellation boundaries
    test_cli.py                   # default TUI and --no-tui forwarding
    test_loader.py                # selected implementation call contract
    ...                           # unchanged step-10 offline suite
```

## Iteration checks

After iteration 1:

- `Repl.banner`, output routing, command handling, and turn execution are
  callable independently without starting an input loop
- command results distinguish quit, handled command, and ordinary input
- callback-driven output never leaks to stdout, while the copied plain REPL
  transcript and injected streams still pass
- readers expose only the session facts the front end needs
- the guide describes the plain fallback and composable REPL without claiming
  the full-screen UI works yet

After iteration 2:

- logger events reach multiple subscribers as isolated mappings after durable
  JSONL writes
- an agent cancellation request is observed at each safe loop/model/tool
  boundary and produces the dedicated cancellation outcome
- cancellation does not corrupt context, leak a worker, or masquerade as an API
  failure
- effective max iterations and normalized token usage are available to the UI
- the guide explains safe cooperative cancellation and its blocking-call limit

After iteration 3:

- headless startup renders conversation, progress, input, and status zones
- resizing gives remaining height to the scrollable conversation without
  hiding input/status at the minimum supported terminal size
- pure event reduction produces correct actions, counts, token totals, and
  token formatting for missing, small, and `k`-scale values
- idle and active rendering include all documented fields and use effective
  rather than hard-coded settings
- the README's layout diagram and field descriptions match tested widgets

After iteration 4:

- Enter routes ordinary text and every slash command correctly and prevents
  concurrent turns
- agent work runs off the UI thread; progress/output events arrive through the
  application message boundary and the spinner/clock remain responsive
- Escape requests one clean interruption, Ctrl+L clears both session and view,
  Page Up/Down scroll, and Ctrl+C/Ctrl+D shut down cleanly
- stale worker messages cannot complete or alter a newer turn
- errors become conversation entries and leave the application usable
- headless UI tests complete without API keys, MCP servers, network, real
  terminal input, timing sleeps, or orphaned threads

After iteration 5:

- `repl()` defaults to the TUI and `repl(tui=False)` retains the plain loop
- `boukensha --no-tui` reaches the selected implementation with `tui=False`;
  no flag selects `tui=True`
- missing Textual fails clearly only on the TUI path
- logger and all MCP clients close on UI exit, interruption, worker failure,
  startup failure, and fallback exit
- `VERSION`, distribution metadata, status bar, and guide agree on `0.11.1`
- README commands use the Python step-11 path and pip workflow; examples are
  accurately described as non-TUI demos
- focused TUI, REPL, cancellation, loader, CLI, and lifecycle tests pass
- the complete offline suite passes and every Python file compiles
- a wheel can be built when the build frontend is available and contains
  `boukensha/tui.py`, loader/CLI modules, MCP subpackages, and the prompt
- step 10 has no tracked changes and no generated artifact, credential, or
  machine-specific path is added
