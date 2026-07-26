# Python Port Plan — 06_the_logger

Port `week1_baseline/ruby/06_the_logger` to
`week1_baseline/python/06_the_logger` as the next self-contained Python
snapshot after `week1_baseline/python/05_agent_loop`.

Current starting point: the Python snapshot was seeded by copying the completed
Python step 5 implementation. The copied directory was named
`06_the _logger`; normalize that copy-time typo to `06_the_logger` before
editing. This plan and the implementation are delta only.

Use an iterative migration. Keep the copied agent loop runnable, add one
coherent behavior at a time, and validate that behavior before proceeding:

1. add runtime flags and the standalone JSONL logger
2. add response metadata, usage normalization, and optional raw events
3. replace console progress output with structured agent-loop events
4. log tool failures as results so the model can recover
5. switch the example, README, public exports, and wrapper to step 6

This step turns the console-only agent loop into an inspectable session:

- create one JSON Lines file per `Logger` instance
- give every event a session ID, timestamp, and phase
- log prompts, loop limits, model responses, tool calls/results, and turn end
- normalize provider token usage before calculating optional model cost
- include raw provider responses only when debug mode is enabled
- preserve the bounded synchronous loop and all provider behavior from step 5
- do not add Python's `logging` framework, log rotation, redaction, streaming,
  async writes, remote sinks, or a log reader

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/06_the_logger/README.md` | session layout, public logger API, debug behavior, and example usage |
| `week1_baseline/ruby/06_the_logger/lib/boukensha/logger.rb` | JSONL event schema, paths, timestamps, token normalization, and cost metadata |
| `week1_baseline/ruby/06_the_logger/lib/boukensha/agent.rb` | logger injection and event placement throughout the loop |
| `week1_baseline/ruby/06_the_logger/lib/boukensha.rb` | runtime flags, cached config, and public logger load |
| `week1_baseline/ruby/06_the_logger/lib/boukensha/prompt_builder.rb` | public backend access used by response logging |
| `week1_baseline/ruby/06_the_logger/examples/example.rb` | logger construction and step-6 demo text |
| `week1_baseline/ruby/bin/06_the_logger` | wrapper entry point |

Also preserve the completed Python step 5 decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/05_agent_loop/boukensha/agent.py` | bounded loop, wrap-up semantics, and dependency injection |
| `week1_baseline/python/05_agent_loop/boukensha/backends/base.py` | provider/model metadata and cost estimation |
| `week1_baseline/python/05_agent_loop/boukensha/context.py` | task, message, and tool state logged by the agent |
| `week1_baseline/python/05_agent_loop/boukensha/prompt_builder.py` | already exposes `backend` as a normal Python attribute |
| `week1_baseline/python/05_agent_loop/boukensha/config.py` | config-directory resolution used for the default session directory |
| `week1_baseline/python/05_agent_loop/examples/example.py` | backend selection and live-example conventions |
| `week1_baseline/python/bin/05_agent_loop` | Python wrapper-script pattern |

Treat unchanged copied files as already migrated. Do not import implementation
code from step 5, and do not intentionally add copied `__pycache__` artifacts.

## Behavior to preserve exactly

1. Constructing a logger creates its destination directory, opens one append
   mode UTF-8 JSONL file, and immediately writes `session_start`.
2. A supplied `session_id` is used unchanged. Otherwise generate
   `<UTC YYYYMMDDTHHMMSSZ>-<8 lowercase hex characters>`.
3. Destination precedence is explicit `log`, then
   `<dir>/<session-id>.jsonl`, then
   `<Boukensha config dir>/sessions/<session-id>.jsonl`.
4. `snapshot` fields are merged into `session_start`. The mandatory
   `session_id` and `at` fields are attached to every event.
5. Each line is one complete JSON object and is flushed immediately so a
   running session can be tailed safely.
6. Timestamps are local timezone-aware ISO 8601 values at whole-second
   precision. Session IDs remain UTC.
7. Event methods and phase fields are:
   `iteration`, `limit_reached`, `turn_end`, `prompt`, `tool_call`,
   `tool_result`, `response`, and debug-only `raw`.
8. Prompt events serialize each message as only `role` and `content`, and
   include both message/tool counts and registered tool names.
9. Tool results are stringified. Successful results use `ok: true`; recovered
   dispatch failures use `ok: false` and include the exception message.
10. Response text is stringified and stripped. Preserve raw provider usage and
    stop reason while also adding compact execution metadata when available.
11. Derive the task name from `task.name` in Python. Derive a provider name
    from the backend class name by converting CamelCase to snake_case.
12. Normalize input tokens from the first available one of
    `input_tokens`, `prompt_tokens`, `promptTokenCount`, or
    `prompt_eval_count`; normalize output tokens from `output_tokens`,
    `completion_tokens`, `candidatesTokenCount`, or `eval_count`.
13. Accept string or integer usage counts through `int(value)`. A missing or
    invalid count becomes `None` instead of breaking logging.
14. Estimate cost only when a backend exposes `estimate_cost` and both token
    counts are present. Let the backend return `None` for unpriced models.
15. Omit unavailable execution-metadata keys, matching Ruby's `compact`.
    Keep ordinary event keys whose value is `None`; JSON encodes them as
    `null`.
16. Raw response events are absent by default and emitted only after the
    package-level debug switch is enabled.
17. The agent accepts an injected logger. When omitted, each agent gets a new
    default `Logger` at construction time; do not instantiate one as a Python
    default argument.
18. Before each normal request, log `iteration` and `prompt`; after the client
    returns, attempt the debug-only `raw` event.
19. On a normal terminal model response, log `response`, then `turn_end` with
    reason `completed`, then return the extracted text.
20. On a tool-use response, log one response event before storing and
    dispatching calls. Use the response's reasoning text, or exactly
    `(tool use — N call)` / `(tool use — N calls)` when it is blank.
21. Log every tool call before dispatch and every tool result afterward.
22. Unlike step 5, recover ordinary tool-dispatch exceptions. Convert the
    result to `ERROR: <ExceptionClass>: <message>`, log it as failed, and add
    it to conversation history so the model can react. Do not catch
    `KeyboardInterrupt`, `SystemExit`, or other `BaseException` subclasses.
23. Preserve assistant-message-before-tool-result ordering and dispatch all
    calls in response order.
24. When the iteration threshold is reached, log `limit_reached` before the
    existing one-call wrap-up path.
25. A successful wrap-up logs `response` and `turn_end`. An `ApiError` logs
    `turn_end` and returns the same deterministic fallback as step 5.
26. The wrap-up request remains outside the iteration counter, disables tools,
    and requests 400 output tokens.
27. Usage extraction for agent response events checks top-level `usage`,
    then `usageMetadata`, then collects Ollama's top-level
    `prompt_eval_count` and `eval_count`. An empty collection becomes `None`.
28. Preserve step 5's transport, parsing, provider replay, task settings,
    iteration threshold, and final-response context behavior.
29. Provide package-level cached config plus quiet/loud and debug switches for
    Ruby API parity. Quiet state is reserved in this step; file logging is not
    user-facing console output and is not suppressed by it.
30. Prior Python snapshots remain standalone and unchanged.

## Python-specific decisions

- Implement `Logger` in `boukensha/logger.py` with `pathlib.Path`,
  `datetime`, `secrets`, `json`, and `re`; no new dependency is needed.
- Store `Logger.path` as a `Path`, use `mkdir(parents=True, exist_ok=True)`,
  and open with `encoding="utf-8"`.
- Use `datetime.now().astimezone().isoformat(timespec="seconds")` for event
  timestamps and `datetime.now(timezone.utc).strftime(...)` for session IDs.
- Use compact `json.dumps(..., separators=(",", ":"))` to match Ruby's
  `JSON.generate`. Let genuinely non-JSON-serializable event data fail
  visibly rather than inventing a lossy serializer.
- Translate Ruby's module methods to `config()`, `quiet()`, `loud()`,
  `is_quiet()`, `debug()`, and `is_debug()`.
- Define runtime state/functions before importing `Logger` and `Agent` in
  `boukensha/__init__.py`, avoiding circular-import workarounds. The logger
  reads `boukensha.config()` and `boukensha.is_debug()` only when needed.
- Keep `PromptBuilder` unchanged: Python step 5 already exposes
  `builder.backend`.
- Catch `Exception` around `Registry.dispatch`, the Python counterpart to
  Ruby's `StandardError`.
- Keep `LoopError` from the Python step 5 public API even though Ruby step 6
  removes its unused type. Removing it would be an unrelated compatibility
  break in this tutorial snapshot.
- Add small deterministic standard-library tests for event shape, debug
  gating, metadata/cost, successful agent logging, tool failure recovery, and
  wrap-up logging. Tests may use temporary directories and fakes; no live API
  call is required.

## Proposed target layout

```text
week1_baseline/python/06_the_logger/
  requirements.txt               # carried forward unchanged
  README.md                       # rewrite for step 6
  boukensha/
    __init__.py                   # runtime switches and Logger export
    agent.py                      # structured event integration
    logger.py                     # new JSONL session logger
    ...                           # copied step-5 implementation
  examples/
    example.py                    # construct Logger and advertise step 6
week1_baseline/python/bin/
  06_the_logger                   # executable wrapper
```

## Iteration checks

After iteration 1:

- importing `boukensha` exposes `Logger` and runtime switches
- constructing/closing a logger yields valid JSONL with `session_start`
- explicit `session_id`, `dir`, `log`, and `snapshot` behave as specified

After iteration 2:

- all event helpers emit their documented phase data
- raw events are debug gated
- Anthropic, OpenAI, Gemini, and Ollama usage key shapes normalize correctly
- priced backends add `cost_usd`; missing/invalid counts do not crash logging

After iteration 3:

- a fake completed response produces
  `iteration → prompt → response → turn_end`
- no step-5 progress lines are printed
- iteration-limit wrap-up logs `limit_reached` and terminal completion data

After iteration 4:

- successful and failing fake tools both become logged tool results
- a failed dispatch becomes a tool-result message and the next model request
  can complete normally

After iteration 5:

- README paths and examples consistently say `06_the_logger`
- `./week1_baseline/python/bin/06_the_logger` resolves the correct snapshot
- every Python file compiles
- deterministic offline tests pass
- step 5 has no tracked changes

## Out of scope

- changing backend request or normalized response formats
- logging HTTP retries inside `Client`
- aggregating turn token totals
- automatic logger ownership/closing in `Agent`
- redaction or truncation policies
- log rotation, retention, querying, visualization, or remote upload
- changing `.boukensha` configuration schemas
