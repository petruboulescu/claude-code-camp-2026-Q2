# Python Port Plan — 08_the_repl_loop

Port `week1_baseline/ruby/08_the_repl_loop` to
`week1_baseline/python/08_the_repl_loop` as the next self-contained Python
snapshot after `week1_baseline/python/07_the_run_dsl`.

Current starting point: the Python step-8 directory was seeded by copying the
completed Python step 7 implementation and is currently identical to it. This
plan and the implementation are delta only.

Use an iterative migration. Keep the copied `run()` snapshot runnable, add one
coherent behavior at a time, and validate that behavior before proceeding:

1. preserve complete conversation history in `Context` and `Agent`
2. add the interactive `Repl` loop and its commands
3. add top-level `repl()` assembly, exports, versioning, and cleanup
4. port the small configuration and HTTP-error deltas
5. add offline tests, then switch the example, README, and wrapper to step 8

This step adds a long-lived interactive entry point alongside the one-shot
runner:

- build and register tools once, before reading input
- reuse one context, registry, prompt builder, client, and logger for the
  whole session
- create a fresh agent for each user turn so the per-turn iteration counter
  and limit reset
- retain user messages, tool-use messages, tool results, and final assistant
  replies across turns
- handle commands locally without sending them to the model
- recover from ordinary agent/API failures and continue prompting
- exit cleanly on `/exit`, `/quit`, end-of-file, or `KeyboardInterrupt`
- preserve `run()` and every provider, DSL, logging, and agent-loop behavior
  from step 7
- do not add async input, readline/history-file integration, streaming, a
  shell parser, or multi-session persistence

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/08_the_repl_loop/README.md` | intended interaction model, commands, and persistent-history behavior |
| `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/repl.rb` | banner, prompt loop, command dispatch, per-turn agent construction, and error recovery |
| `week1_baseline/ruby/08_the_repl_loop/lib/boukensha.rb` | top-level `repl` wiring, configuration resolution, logger ownership, and interrupt handling |
| `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/context.rb` | conversation clearing without removing tools |
| `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/agent.rb` | persistence of terminal assistant replies |
| `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/config.rb` | current-directory `.boukensha` discovery |
| `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/client.rb` | clearer authentication failure |
| `week1_baseline/ruby/08_the_repl_loop/lib/boukensha/version.rb` | version exposed in the REPL banner |
| `week1_baseline/ruby/08_the_repl_loop/examples/example.rb` | interactive two-tool example |

Also preserve the completed Python step 7 decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/07_the_run_dsl/boukensha/run_dsl.py` | Python provider assembly, default resolution, and `configure(dsl)` convention |
| `week1_baseline/python/07_the_run_dsl/boukensha/__init__.py` | cached config, runtime flags, and public exports |
| `week1_baseline/python/07_the_run_dsl/boukensha/agent.py` | bounded loop and explicit per-turn limits |
| `week1_baseline/python/07_the_run_dsl/boukensha/logger.py` | JSONL `turn` event, subscribers, and close semantics |
| `week1_baseline/python/07_the_run_dsl/tests/` | standard-library offline test style |
| `week1_baseline/python/bin/07_the_run_dsl` | Python wrapper-script pattern |

Treat unchanged copied files as already migrated. Do not import implementation
code from step 7, and do not intentionally add copied `__pycache__` artifacts.

## Behavior to preserve exactly

1. Export a top-level `repl()` function and a `Repl` class from `boukensha`;
   keep `run()` and `RunDSL` public and unchanged.
2. Give `repl()` the same options and default-resolution rules as `run()`,
   except that it has no `task` argument:
   `repl(*, system=None, model=None, backend=None, api_key=None,
   ollama_host="http://localhost:11434", log=None,
   max_output_tokens=None, configure=None)`.
3. The runner always uses `PLAYER` and the package-level cached `config()`.
4. Resolve `system`, `model`, `backend`, `api_key`, and
   `max_output_tokens` exactly as step 7 does. Defaults apply only when an
   argument is `None`, not merely falsey.
5. Support the same five provider strings and constructor arguments as
   `run()`: `anthropic`, `openai`, `gemini`, `ollama`, and `ollama_cloud`.
6. Reuse the step-7 `RunDSL` callback convention. If present, call
   `configure(dsl)` exactly once, before backend/client/logger construction
   and before reading interactive input.
7. Construct one `Context`, `Registry`, backend, `PromptBuilder`, `Client`,
   and `Logger` for the complete REPL session.
8. Write one `session_start` snapshot with the effective task, iteration
   limit, output-token limit, model, and provider.
9. `Context.clear_messages()` removes all conversation messages while
   retaining the task, system prompt, and registered tools.
10. Whenever `Agent.run()` obtains terminal model text, add that text to the
    context as an `assistant` message before returning it.
11. Persist assistant output in all three terminal paths: ordinary
    completion, successful iteration-limit wrap-up, and the fallback message
    returned when the wrap-up API call raises `ApiError`.
12. Do not add an assistant message for an exception that escapes
    `Agent.run()`.
13. Preserve the existing tool-use transcript: assistant tool calls and tool
    results remain in the same shared context before the eventual final
    assistant message.
14. `Repl` receives the already constructed objects and effective runtime
    values. It does not resolve configuration or own the logger.
15. `Repl.start()` prints a banner, displays the exact prompt
    `boukensha> `, flushes it, reads one line, strips surrounding whitespace,
    and ignores empty input.
16. Ordinary input increments the REPL turn number, writes
    `logger.turn(n=...)`, adds a user message, constructs a fresh `Agent`,
    runs it, and prints its result.
17. Reconstructing `Agent` per user input is intentional: conversation state
    persists in `Context`, while `Agent.iteration` starts at zero and the
    action limit applies independently to each interactive turn.
18. Tool registration and the expensive/shared provider objects are not
    rebuilt between turns.
19. Handle `/help`, `/quiet`, `/loud`, `/clear`, `/exit`, and `/quit`
    locally and case-sensitively. Commands never enter the context and never
    call the model.
20. `/help` prints the command list and continues.
21. `/quiet` calls the existing package quiet switch, `/loud` calls the
    existing loud switch, and both print confirmation. Do not redesign logger
    verbosity in this step: the existing JSONL logger remains the durable
    record and final answers remain visible.
22. `/clear` calls `context.clear_messages()`, resets the displayed/logged
    REPL turn counter to zero, prints confirmation, and leaves tools and
    system state intact.
23. `/exit` and `/quit` print `Goodbye.` and end the session.
24. End-of-file ends the session without treating it as an error.
25. Catch `LoopError` and `ApiError` around one turn, print a concise error,
    and return to the prompt without discarding conversation history.
26. Do not catch unexpected per-turn exceptions; programming errors remain
    visible.
27. Catch `KeyboardInterrupt` at the top-level `repl()` boundary, print
    `Interrupted.`, and return normally.
28. Always close the runner-owned logger in a `finally` block after normal
    exit, EOF, `/exit`, a handled interrupt, or an escaping exception. Do not
    close a logger that was never constructed.
29. Provide `VERSION = "0.8.0"` and use it in the banner. The banner also
    reports the resolved config directory and provider/model without exposing
    the API-key value.
30. Update `Config` directory precedence to: explicit `BOUKENSHA_DIR`, an
    existing `.boukensha` directory under the current working directory,
    then `~/.boukensha`.
31. Preserve the cached-config rule: changing the working directory does not
    silently replace an already constructed package config object.
32. Report an HTTP 401 as `authentication failed (401) — check your API key`
    without retrying it. Preserve all other retry counts and error messages.
33. Prior Python snapshots remain standalone and unchanged.

## Python-specific decisions

- Put `Repl` in `boukensha/repl.py` and `VERSION` in
  `boukensha/version.py`.
- Keep assembly in `boukensha/run_dsl.py`, beside the existing shared helper
  functions. Add `repl()` there instead of duplicating provider selection in
  `__init__.py`.
- Export `Repl`, `VERSION`, and `repl` through `boukensha.__init__`.
- Use `sys.stdin.readline()` and `sys.stdout` (or small internal
  read/write helpers) rather than `input()` so tests can supply `StringIO`
  streams and assert prompts without replacing global builtins. Stream
  injection, if added, stays an internal `Repl` constructor concern and is
  not added to the public `repl()` signature.
- Treat `readline() == ""` as EOF. Strip `\r\n` and surrounding whitespace
  with `strip()`, matching Ruby.
- Use `print(..., file=output_stream)` and explicitly flush the prompt.
- Name the context method `clear_messages()`; Python does not encode mutation
  with Ruby's trailing `!`.
- Append the assistant message only after response logging and `turn_end`
  succeed, matching the Ruby ordering.
- Factor the common step-7/step-8 assembly only when doing so keeps `run()`
  behavior and cleanup obvious. Do not introduce a broad container or public
  dependency-injection API.
- Initialize `logger = None` before the guarded REPL assembly and conditionally
  close it in `finally`, as in `run()`.
- On local Ollama, the absence of an API key is expected. The banner may say
  that no key is required rather than displaying a misleading failure mark.
- Make the 401 special case in the common HTTP error formatter so both
  `HTTPError` and defensive non-2xx response paths produce the same result.
- Correct Ruby README/example drift while porting: call this Step 8, use
  `08_the_repl_loop` paths, document all six commands (including `/quiet` and
  `/loud`), and do not claim the file logger prints detailed phases to
  stdout.
- Add standard-library `unittest` coverage with fake clients and
  `io.StringIO`. No terminal automation, live API, provider SDK, or new
  dependency is required.

## Proposed target layout

```text
week1_baseline/python/08_the_repl_loop/
  requirements.txt               # carried forward unchanged
  README.md                       # rewrite for the step-8 interactive runner
  boukensha/
    __init__.py                   # export Repl, VERSION, and repl
    version.py                    # VERSION = "0.8.0"
    repl.py                       # interactive loop and command handling
    run_dsl.py                    # add top-level repl() assembly
    context.py                    # clear_messages()
    agent.py                      # persist terminal assistant replies
    config.py                     # cwd-local config discovery
    client.py                     # explicit 401 diagnostic
    ...                           # copied step-7 implementation
  examples/
    example.py                    # configure tools and enter repl()
  tests/
    test_agent.py                 # terminal reply persistence
    test_config.py                # config-directory precedence
    test_client.py                # 401 behavior
    test_repl.py                  # commands, history, errors, and cleanup
    test_logger.py                # carried forward unchanged
    test_run_dsl.py               # carried forward plus repl assembly tests
week1_baseline/python/bin/
  08_the_repl_loop               # executable wrapper
```

If the copied snapshot does not yet have the named focused test files, create
them; do not move unrelated step-7 tests merely to match this layout.

## Iteration checks

After iteration 1:

- `Context.clear_messages()` empties messages but preserves system/task/tools
- a normal terminal reply becomes the final assistant context message
- wrap-up text and the `ApiError` fallback also become assistant messages
- an escaping error does not invent an assistant reply
- every existing step-7 agent test still passes

After iteration 2:

- scripted input can exercise the loop completely offline
- two prompts create two fresh agents but share one accumulating context
- turn events are numbered `1`, `2`, and so on
- blank lines and all six commands avoid model calls
- `/clear` resets messages and numbering without unregistering tools
- `LoopError` and `ApiError` affect one turn only
- EOF and command exits terminate predictably

After iteration 3:

- importing `Repl`, `VERSION`, and `repl` from `boukensha` works
- every provider is assembled with the same effective values as `run()`
- tool setup happens once and tools are visible on the first turn
- `/exit`, EOF, `KeyboardInterrupt`, and escaping exceptions all close the
  single logger
- `run()` remains a one-shot entry point with unchanged results and cleanup

After iteration 4:

- config lookup honors explicit, current-directory, and home precedence
- cached config behavior remains deterministic
- HTTP 401 gets the authentication-specific message and is not retried
- other HTTP and transport retry tests are unchanged

After iteration 5:

- README and example consistently say `08_the_repl_loop` and Step 8
- the example demonstrates `configure(dsl)` plus the decorator API
- `./week1_baseline/python/bin/08_the_repl_loop` resolves the correct snapshot
- no live API is needed to run the deterministic test suite
- every Python file compiles and all offline tests pass
- step 7 has no tracked changes
- no `__pycache__` or `.pyc` artifact is added

## Out of scope

- changing or removing the one-shot `run()` API
- persisting transcript history between processes
- multiple named conversations or session resume
- readline completion, arrow-key history, prompt-toolkit, or a TUI
- slash-command arguments, aliases beyond `/quit`, or shell escapes
- async input/tools, streaming responses, or concurrent turns
- recreating the backend/client for every turn
- changing the configured task away from `PLAYER`
- a public max-iterations override
- swallowing unexpected tool, setup, configuration, or programming errors
- redesigning the quiet/loud or debug logging model
