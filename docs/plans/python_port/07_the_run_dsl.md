# Python Port Plan — 07_the_run_dsl

Port `week1_baseline/ruby/07_the_run_dsl` to
`week1_baseline/python/07_the_run_dsl` as the next self-contained Python
snapshot after `week1_baseline/python/06_the_logger`.

Current starting point: the Python step-7 directory was seeded by copying the
completed Python step 6 implementation and is currently identical to it. This
plan and the implementation are delta only.

Use an iterative migration. Keep the copied logger snapshot runnable, add one
coherent behavior at a time, and validate that behavior before proceeding:

1. add the small `RunDSL` tool-registration host
2. add provider selection and top-level `run()` wiring
3. guarantee logger cleanup and port the small logger observer delta
4. add deterministic offline tests for the public entry point
5. switch the example, README, public exports, and wrapper to step 7

This step replaces manual construction of the agent object graph with one
public entry point:

- accept a task string and optional system/model/provider/runtime overrides
- resolve omitted values from the cached player-task configuration
- construct the context, registry, backend, prompt builder, client, logger,
  and agent internally
- expose only tool registration to the setup callback
- support Anthropic, OpenAI, Gemini, Ollama, and Ollama Cloud
- add the user task, execute the existing bounded loop, and return its result
- always close the logger owned by `run()`
- preserve every provider, agent-loop, and JSONL behavior from step 6
- do not add global tool state, dependency injection to the public runner,
  async execution, streaming, context managers, or a general task selector

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/07_the_run_dsl/README.md` | intended public entry point, options, and before/after usage |
| `week1_baseline/ruby/07_the_run_dsl/lib/boukensha/run_dsl.rb` | deliberately narrow DSL host and tool delegation |
| `week1_baseline/ruby/07_the_run_dsl/lib/boukensha.rb` | config resolution, backend selection, object wiring, execution, and cleanup |
| `week1_baseline/ruby/07_the_run_dsl/lib/boukensha/logger.rb` | new `turn` event and synchronous subscriber hook |
| `week1_baseline/ruby/07_the_run_dsl/examples/example.rb` | concise runner usage and two-tool example |
| `week1_baseline/ruby/bin/07_the_run_dsl` | wrapper entry point |

Also preserve the completed Python step 6 decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/06_the_logger/boukensha/__init__.py` | cached config, runtime switches, and public exports |
| `week1_baseline/python/06_the_logger/boukensha/registry.py` | Python tool-registration signature |
| `week1_baseline/python/06_the_logger/boukensha/tasks/base.py` | player defaults and task-setting resolution |
| `week1_baseline/python/06_the_logger/boukensha/tasks/player.py` | singleton `PLAYER` task used by the runner |
| `week1_baseline/python/06_the_logger/boukensha/backends/` | provider constructors and supported model validation |
| `week1_baseline/python/06_the_logger/boukensha/agent.py` | task settings, explicit runtime limits, and logger injection |
| `week1_baseline/python/06_the_logger/boukensha/logger.py` | session snapshot and close semantics |
| `week1_baseline/python/06_the_logger/examples/example.py` | file-tool behavior and repository-relative paths |
| `week1_baseline/python/bin/06_the_logger` | Python wrapper-script pattern |

Treat unchanged copied files as already migrated. Do not import implementation
code from step 6, and do not intentionally add copied `__pycache__` artifacts.

## Behavior to preserve exactly

1. Export a top-level `run()` function and a `RunDSL` class from
   `boukensha`.
2. `task` is required and becomes the first user message immediately before
   the agent starts.
3. The runner always uses the `PLAYER` task and reads its settings through
   the package-level cached `config()` object.
4. An omitted system prompt comes from `PLAYER.system_prompt(...)`, using the
   configured user prompts directory and this snapshot's shipped prompts
   directory.
5. Omitted model and provider values come from `PLAYER.model(settings)` and
   `PLAYER.provider(settings)`.
6. Resolve defaults only when an argument is `None`. Do not let normal Python
   truthiness accidentally replace an explicitly supplied empty string.
7. Accept provider names as Python strings:
   `"anthropic"`, `"openai"`, `"gemini"`, `"ollama"`, and
   `"ollama_cloud"`.
8. When `api_key` is omitted, read `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`,
   `GEMINI_API_KEY`, or `OLLAMA_API_KEY` after `config()` has loaded the
   configured `.env` file. Local Ollama does not require a key.
9. Construct each existing backend with the same arguments used by the
   manual step-6 example. Pass `ollama_host` only to `Ollama`; its default is
   `http://localhost:11434`.
10. Reject any other provider with `ValueError`. The message must name the
    rejected value and list all five accepted names.
11. Construct `Context(task=PLAYER, system=...)` and its `Registry` before
    invoking the tool-setup callback.
12. `RunDSL` holds only the registry and exposes only public tool
    registration behavior. It must not expose the context, backend, client,
    logger, or agent as public attributes.
13. `RunDSL.tool()` delegates name, description, parameter schema, and
    callable to `Registry.tool()` without changing their meaning.
14. Support idiomatic decorator registration:

    ```python
    def configure(dsl):
        @dsl.tool(
            "read_file",
            description="Read a file",
            parameters={"path": {"type": "string"}},
        )
        def read_file(path):
            return Path(path).read_text(encoding="utf-8")
    ```

15. Also accept `func=` directly so programmatic callers need not use a
    decorator. In either form return the original callable, matching normal
    Python decorator expectations. Reject supplying a non-callable function
    with `TypeError`.
16. The setup callback is optional. When supplied, call it exactly once with
    the `RunDSL` instance before backend/client/agent construction.
17. Build `PromptBuilder`, `Client`, and `Agent` from the resolved objects
    without changing their existing APIs.
18. Resolve `max_iterations` from `PLAYER.max_iterations(settings)`. Step 7
    does not add a public `max_iterations` override because Ruby does not
    expose one.
19. Resolve `max_output_tokens` from the task settings unless the caller
    supplied an explicit value, then pass the effective values and the task
    settings into `Agent`.
20. Construct one `Logger` with the optional explicit `log` path and a
    `session_start` snapshot containing task name, effective iteration limit,
    effective output-token limit, model, and provider.
21. Add the user message only after all construction and tool registration
    succeeds, then return `agent.run()` unchanged.
22. Close the runner-owned logger in a `finally` block on success, on an
    agent exception, and on `BaseException` subclasses such as
    `KeyboardInterrupt`. Do not close a logger that was never constructed.
23. Do not swallow or translate configuration, setup, backend-construction,
    client, or agent errors.
24. Keep direct construction of `Context`, `Registry`, backends,
    `PromptBuilder`, `Client`, `Logger`, and `Agent` public and working; the
    runner is a convenience API, not a replacement API.
25. Add `Logger.turn(n=...)`, emitting the ordinary JSONL event
    `{"phase":"turn","n":...}` with the existing session metadata.
26. Add `Logger.subscribe(callback)`. Subscribers are retained in
    registration order and synchronously receive each phase-specific event
    after that event has been written and flushed.
27. A subscriber receives the original phase event, without the logger-added
    `session_id` and `at` fields, matching Ruby. Subscriber exceptions remain
    visible to the caller.
28. `session_start` occurs during logger construction, before callers can
    subscribe; subscriptions observe only later events.
29. Preserve all step-6 logging, debug gating, provider transport, response
    parsing, tool recovery, iteration limits, and wrap-up behavior.
30. Prior Python snapshots remain standalone and unchanged.

## Python-specific decisions

- Put `RunDSL` in `boukensha/run_dsl.py`; keep assembly helpers in that module
  instead of further enlarging `boukensha/__init__.py`.
- Use `run(*, task, system=None, model=None, backend=None, api_key=None,
  ollama_host="http://localhost:11434", log=None,
  max_output_tokens=None, configure=None)`.
- Python has no Ruby block plus `instance_eval` equivalent that is both
  idiomatic and safe. Translate the block to `configure(dsl)`, and translate
  the nested Ruby tool block to a `@dsl.tool(...)` decorator.
- Implement `RunDSL.tool(..., func=None)` as a decorator factory when `func`
  is omitted and as immediate registration when it is present. Internally,
  pass the function using the existing keyword-only `Registry.tool(...,
  func=...)` API.
- Do not use module-level mutable state to make bare `tool(...)` calls work.
  It would leak registrations between concurrent or nested runs.
- Compare provider strings directly. Do not introduce an enum solely to
  imitate Ruby symbols.
- Use `os.environ.get()` for key lookup. Let existing backend behavior decide
  what a missing key means; the runner should not add provider-specific
  validation absent from the Ruby step.
- Keep the resolved backend object in a local variable named distinctly from
  the provider-name argument.
- Initialize `logger = None` before the guarded assembly section and close it
  in `finally` only after successful construction.
- Store subscribers in a per-instance list initialized before
  `session_start`. Iterate over a shallow tuple copy so a callback may safely
  subscribe another callback without changing the current delivery pass.
- Pass each subscriber a shallow copy of the phase event. This protects the
  logger's internal event mapping while preserving nested values and Ruby's
  pre-metadata event shape.
- Correct source-documentation drift while porting: call this Step 7, list
  all five providers, use `max_output_tokens` rather than the stale
  `max_tokens`/`token_budget` names, and do not claim that the file logger
  prints phases to stdout.
- Add standard-library `unittest` coverage with fakes/mocks. No live API,
  provider SDK, or new dependency is required.

## Proposed target layout

```text
week1_baseline/python/07_the_run_dsl/
  requirements.txt               # carried forward unchanged
  README.md                       # rewrite for the step-7 public runner
  boukensha/
    __init__.py                   # export RunDSL and run
    run_dsl.py                    # new DSL host and object-graph assembly
    logger.py                     # turn event and subscriber delta
    ...                           # copied step-6 implementation
  examples/
    example.py                    # configure tools and call run()
  tests/
    test_logger.py                # carried forward plus subscriber tests
    test_run_dsl.py               # new deterministic runner tests
week1_baseline/python/bin/
  07_the_run_dsl                  # executable wrapper
```

## Iteration checks

After iteration 1:

- importing `RunDSL` directly from `boukensha.run_dsl` works
- decorator and direct `func=` registration both produce ordinary registry
  tools
- registered callables dispatch with keyword arguments
- the DSL host exposes no assembly internals

After iteration 2:

- each of the five provider names constructs the matching backend with the
  correct key/model/host values
- omitted values resolve from the cached player configuration
- invalid providers fail before any network request
- the runner constructs the existing object graph, adds the task message,
  and returns the agent result

After iteration 3:

- runner-created loggers close after both successful and failed agent runs
- `turn` writes a valid event
- multiple subscribers run in order after the JSONL line has been flushed
- subscriber payloads omit session metadata and subscriber failures surface

After iteration 4:

- a fake terminal response can exercise `run()` completely offline
- configured tools are visible to the first prompt
- explicit overrides beat config defaults
- the session snapshot contains the effective values
- setup and agent exceptions do not leak an open log file

After iteration 5:

- README and example consistently say `07_the_run_dsl` and Step 7
- the example demonstrates the `configure(dsl)` plus decorator API without
  manual plumbing
- `./week1_baseline/python/bin/07_the_run_dsl` resolves the correct snapshot
- every Python file compiles
- all deterministic offline tests pass
- step 6 has no tracked changes

## Out of scope

- selecting task types other than `PLAYER`
- a public max-iterations override
- accepting prebuilt backends, clients, agents, registries, or loggers
- changing provider/model validation or task configuration schemas
- global or thread-local DSL state that enables bare `tool(...)` calls
- async setup callbacks, async tools, streaming responses, or streaming logs
- automatic retries outside the existing `Client`
- changing logger event metadata or replaying `session_start` to subscribers
- terminal UI output, remote observers, subscription removal, or event queues
- changing `.boukensha` MUD connection settings
