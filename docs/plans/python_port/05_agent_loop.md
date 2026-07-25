# Python Port Plan — 05_agent_loop

Port `week1_baseline/ruby/05_agent_loop` to
`week1_baseline/python/05_agent_loop` as the next self-contained Python
snapshot after `week1_baseline/python/04_api_client`.

Current starting point: `week1_baseline/python/05_agent_loop` has already been
seeded by copying the completed Python `04_api_client` snapshot. This plan and
the implementation are therefore delta only.

Use an iterative migration: keep the copied step runnable, add one coherent
layer at a time, and validate that layer before moving to the next one. The
recommended iterations are:

1. add the common response contract and provider parsers
2. make normalized assistant tool calls round-trip through request history
3. add tool suppression and task limits
4. add and test the agent loop
5. switch the example, README, and wrapper to step 5

This step turns the one-shot API client into a bounded, synchronous tool-use
loop:

- preserve the Python API-client snapshot's transport, retry behavior, layout,
  and public APIs unless Ruby step 5 explicitly changes them
- normalize all five providers' responses into one internal content-block
  shape
- preserve assistant tool-call messages when rebuilding provider payloads
- dispatch every tool call in a response and append its result to the context
- repeat model calls until the provider reports a normal end turn
- stop starting work after a configurable iteration threshold and make one
  tools-disabled wrap-up call
- keep the implementation synchronous and standard-library only
- do not add streaming, async execution, parallel tool dispatch, persistence,
  approval policies, or general loop recovery

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/05_agent_loop/README.md` | loop contract, normalized response shape, task settings, and teaching notes |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/agent.rb` | new loop, tool dispatch, iteration threshold, wrap-up call, and fallback text |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/backends/anthropic.rb` | Anthropic response normalization and tools override |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/backends/openai.rb` | OpenAI parsing plus assistant tool-call reconstruction |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/backends/gemini.rb` | Gemini parsing, synthetic IDs, and assistant-part reconstruction |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/backends/ollama.rb` | local Ollama parsing, synthetic IDs, and assistant-message reconstruction |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/backends/ollama_cloud.rb` | hosted Ollama equivalent of the local Ollama changes |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/prompt_builder.rb` | adds response parsing and forwards the tools override |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/client.rb` | forwards the tools override into each request payload |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/tasks/base.rb` | integer-backed iteration and output-token settings with defaults |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha/errors.rb` | adds the reserved `LoopError` type |
| `week1_baseline/ruby/05_agent_loop/lib/boukensha.rb` | adds `Agent` to the public load surface |
| `week1_baseline/ruby/05_agent_loop/examples/example.rb` | changes the live demo from raw JSON to a complete tool-use turn |
| `week1_baseline/ruby/bin/05_agent_loop` | wrapper entry point |

Also read the completed previous Python port for all carry-forward decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/04_api_client/boukensha/client.py` | HTTP behavior and retry/error contract to preserve |
| `week1_baseline/python/04_api_client/boukensha/prompt_builder.py` | existing builder facade to extend |
| `week1_baseline/python/04_api_client/boukensha/context.py` | message history and tool storage mutated by the loop |
| `week1_baseline/python/04_api_client/boukensha/registry.py` | synchronous keyword-argument tool dispatch |
| `week1_baseline/python/04_api_client/boukensha/message.py` | assistant content blocks and tool-result IDs |
| `week1_baseline/python/04_api_client/boukensha/backends/*.py` | provider payload formats that must gain parsing and round-trip support |
| `week1_baseline/python/04_api_client/boukensha/tasks/base.py` | Python task API to extend with loop settings |
| `week1_baseline/python/04_api_client/boukensha/__init__.py` | public exports to preserve and extend |
| `week1_baseline/python/04_api_client/examples/example.py` | backend selection and live-example conventions |
| `week1_baseline/python/04_api_client/README.md` | prior step's documented client contract |
| `week1_baseline/python/bin/04_api_client` | wrapper-script pattern |

The copied `week1_baseline/python/05_agent_loop` snapshot is currently
identical to Python step 4. Treat every unchanged file as already migrated;
only add or edit the files named by this plan. Ignore copied `__pycache__`
artifacts when comparing snapshots and do not intentionally add them.

## Behavior to preserve exactly

1. **One normalized response shape drives the loop**:

   ```python
   {
       "stop_reason": "tool_use" or "end_turn",
       "content": [
           {"type": "text", "text": "..."},
           {
               "type": "tool_use",
               "id": "...",
               "name": "...",
               "input": {...},
           },
       ],
   }
   ```

   `Agent` must not branch on provider names or raw provider response keys.
2. **Each backend owns both directions of conversion**. `parse_response`
   converts raw JSON into normalized blocks; request serialization converts
   stored normalized assistant blocks back to that provider's wire format.
3. **Anthropic content already matches the common block format**. Preserve its
   raw content array and map only the stop reason: exactly `"tool_use"` remains
   `"tool_use"`; every other or missing value becomes `"end_turn"`.
4. **OpenAI reads the first choice's message**. Preserve optional text, parse
   each function's JSON `arguments` string into a Python dictionary, and retain
   the provider's tool-call ID. Treat any non-`None` text value, including an
   empty string, as present, matching Ruby truthiness. Invalid argument JSON
   remains a standard `json.JSONDecodeError`.
5. **Gemini reads the first candidate's content parts**. Convert
   `functionCall` parts to tool-use blocks and text parts to text blocks. It
   has no provider call ID, so reuse the function name as both `id` and
   `name`. Preserve a text part whenever its text value is non-`None`.
6. **Ollama and Ollama Cloud read `message.content` and
   `message.tool_calls`**. Include non-empty text, convert each function call,
   and reuse the function name as the call ID.
7. **Tool use wins the stop decision**. OpenAI, Gemini, Ollama, and Ollama
   Cloud return `"tool_use"` whenever at least one tool call exists, even when
   the same response also contains text.
8. **The assistant tool-use message is stored before its tool results**.
   Append one assistant message containing the complete normalized content
   list, then append each tool-result message in response order.
9. **All tool calls in one model response are dispatched before the next API
   call**. Dispatch synchronously through `Registry.dispatch(name, args)`.
10. **Tool results are converted with `str(result)`** before being logged and
    stored. Each result message uses the matching normalized `id` as
    `tool_use_id`.
11. **A non-tool response ends the loop**. Concatenate the text of all
    normalized text blocks in order and return it. Ignore non-text blocks for
    final text extraction. Matching Ruby, do not append this final assistant
    response to the context.
12. **The default work threshold is 25 model iterations**. A positive
    `max_iterations` stops new work once the completed iteration count reaches
    that value. `0` or a negative value disables the threshold.
13. **The threshold is not a hard total-call cap**. On reaching it, perform
    exactly one additional terminal wrap-up call outside the counted loop.
    Do not increment the iteration counter or re-check the threshold for that
    call.
14. **Wrap-up mutates the conversation first** by adding the exact directive:

    ```text
    You have reached your action limit for this turn. Do not call any more tools.
    Briefly summarize what you accomplished, what is still unfinished, and the
    single next action you would take.
    ```

15. **The wrap-up request disables tools** with `tools=[]` and always requests
    `400` output tokens. This deliberately overrides both registered tools and
    the normal configured output-token setting.
16. **A useful wrap-up response is returned** after normal parsing and text
    extraction. Empty or whitespace-only text produces the deterministic
    fallback:

    ```text
    I reached my <limit>-action limit for this turn before finishing
    (max_iterations). Ask me to continue and I'll pick up from here.
    ```

    Render this as one line in the actual Python string.
17. **Only `ApiError` from the terminal wrap-up request is recovered** into
    the same fallback. Parsing errors, tool errors, provider-shape errors, and
    failures during normal work iterations continue to surface.
18. **Configuration precedence matches Ruby**:
    explicit constructor argument, then task setting when `task_settings` was
    supplied, then the agent/task default. Explicit
    `max_iterations` is integer-coerced.
19. **Normal model calls inherit the configured `max_output_tokens`**. If no
    value is resolved, omit the argument so `Client.call` retains its `1024`
    default.
20. **`tools=None` and `tools=[]` have different meanings** throughout the
    request path. `None` means serialize the context registry; an explicit
    list, especially `[]`, is sent unchanged.
21. **Provider call IDs round-trip correctly**. Anthropic and OpenAI preserve
    real IDs. Gemini and both Ollama backends use the function name because
    their step-5 request/result pairing is name-based.
22. **The client transport is otherwise unchanged**. Preserve request
    encoding, retry statuses, transient-error handling, four-attempt maximum,
    deterministic backoff, TLS verification, raw JSON decoding, and
    `ApiError` messages from step 4.
23. **The loop logs progress to standard output**: one iteration line, plus a
    tool-call and truncated tool-result line for every dispatched call. Do not
    introduce a logging dependency.
24. **One `Agent` instance retains its iteration count**. Initialize the count
    in the constructor and do not reset it at the start of `run`; the example
    creates a fresh agent for its single turn.
25. **Prior snapshots remain standalone and unchanged**. Step 5 must not
    import implementation code from Python step 4.

## Ruby differences not to copy blindly

- Ruby step 5 changes `Config::PROMPTS_DIR` from `../../prompts` to
  `../../../prompts`. From `lib/boukensha/config.rb`, that moves the lookup
  outside the standalone snapshot and does not match the README contract.
  Python step 4 already resolves its own `prompts/` directory correctly; keep
  `boukensha/config.py` unchanged.
- Ruby's compact `mud_host`, `mud_port`, `mud_username`, and `mud_password`
  rewrites are syntax-only. Keep the existing Python config methods unchanged.
- Ruby adds `LoopError`, but the final Ruby `Agent` does not raise it: reaching
  the threshold triggers graceful wrap-up. Add the Python error and export for
  source parity, but do not manufacture a use for it.
- The Ruby README's run path omits the `ruby/` snapshot segment. The Python
  guide and README must use
  `./week1_baseline/python/bin/05_agent_loop`.
- The README's sample iteration output predates the final Ruby log format.
  Python should follow `agent.rb` and print `[iteration N/LIMIT]`.

## Python-specific decisions

- Represent normalized responses as ordinary dictionaries and lists. Use
  string keys consistently so backend output can be stored directly as
  `Message.content` and replayed without another model type.
- Add `parse_response(response)` to each backend rather than to the HTTP
  client. `Client` must continue returning raw decoded provider JSON.
- In OpenAI, use `json.loads(arguments or "{}")` and `json.dumps(input)` for
  the inverse conversion.
- Let absent provider nodes degrade to empty dictionaries/lists in the same
  places Ruby uses `|| {}` or `|| []`; do not add a large validation layer in
  this tutorial step.
- Assistant history may still contain a plain string from earlier code. The
  OpenAI, Gemini, Ollama, and Ollama Cloud reverse serializers must treat that
  as one normalized text block for backward compatibility.
- For provider messages rebuilt from normalized blocks:

  | Backend | Assistant replay |
  |---------|------------------|
  | Anthropic | `{"role": "assistant", "content": blocks}` unchanged |
  | OpenAI | join text into `content`; emit `tool_calls` with JSON-string arguments |
  | Gemini | emit `role: "model"` with text and `functionCall` parts in block order |
  | Ollama / Ollama Cloud | join text into `content`; emit function `tool_calls` |

- Extend every backend's `to_payload` to accept `tools=None`. Choose the
  registry-derived schema only with `tools is None`; do not use truthiness,
  because `[]` must suppress tools.
- Extend `PromptBuilder.to_api_payload` and `Client.call` with the same
  `tools=None` keyword and forward it unchanged. Add
  `PromptBuilder.parse_response` as a direct backend delegation.
- Add `Task.DEFAULT_MAX_ITERATIONS = 25` and
  `Task.DEFAULT_MAX_OUTPUT_TOKENS = 1024`, plus `max_iterations(settings)` and
  `max_output_tokens(settings)`. A small private integer-setting helper should
  return the default only for a missing/`None` value and otherwise call
  `int(value)`, allowing invalid configuration to fail visibly.
- Keep `Agent` dependency-injected: accept the context, registry, builder, and
  client instead of constructing them internally. Keyword-only arguments are
  preferred for parity with the Ruby initializer and to make tests legible.
- Use a normal `while True` loop. Check the iteration threshold before
  incrementing, increment exactly once for each normal model call, and keep
  wrap-up outside that counter.
- Python slicing naturally provides the Ruby result preview:
  `str(result)[:61]`. Preserve the pedagogical output but do not build a
  configurable logger yet.
- Do not catch `UnknownToolError`, callback exceptions, `JSONDecodeError`,
  `TypeError`, or `KeyboardInterrupt` in `Agent.run`.
- Do not add a new dependency. The copied `requirements.txt` remains
  unchanged.

## Proposed target layout

```text
week1_baseline/python/05_agent_loop/
  requirements.txt               # carried forward unchanged
  README.md                       # rewrite for step 5
  boukensha/
    __init__.py                   # export Agent and LoopError
    agent.py                      # new bounded synchronous tool-use loop
    client.py                     # forward optional tools override
    config.py                     # carried forward unchanged
    context.py                    # carried forward unchanged
    errors.py                     # add LoopError
    message.py                    # carried forward unchanged
    prompt_builder.py             # forward tools and delegate response parsing
    registry.py                   # carried forward unchanged
    tool.py                       # carried forward unchanged
    backends/
      anthropic.py                # parse response; accept tools override
      openai.py                   # parse and replay assistant tool calls
      gemini.py                   # parse and replay function-call parts
      ollama.py                   # parse and replay assistant tool calls
      ollama_cloud.py             # same hosted-Ollama behavior
      base.py                     # carried forward unchanged
      __init__.py                 # carried forward unchanged
    tasks/
      base.py                     # add iteration/output-token settings
      player.py                   # carried forward unchanged
      __init__.py                 # carried forward unchanged
  prompts/
    system.md                     # carried forward unchanged
  examples/
    example.py                    # run a complete tool-use turn
week1_baseline/python/bin/05_agent_loop
```

Each numbered step remains a standalone snapshot; do not import implementation
code from `python/04_api_client`.

## API plan

### `LoopError`

Extend `boukensha/errors.py` without changing the existing exceptions:

```python
class LoopError(Exception):
    pass
```

Export it for parity with Ruby step 5. It is reserved for later loop failure
policies and is not raised by this bounded, graceful-wrap-up implementation.

### Backend response contract

Every concrete backend gains:

```python
def parse_response(self, response):
    return {
        "stop_reason": "tool_use" or "end_turn",
        "content": normalized_blocks,
    }
```

Keep parsing provider-local:

- Anthropic: `response["content"]` and `response["stop_reason"]`
- OpenAI: `response["choices"][0]["message"]`
- Gemini: `response["candidates"][0]["content"]["parts"]`
- Ollama and Ollama Cloud: `response["message"]`

Use defensive `.get(...)` traversal where Ruby uses `dig(...) || {}` or
`|| []`, including an absent first choice/candidate. Do not interpret usage,
finish reasons beyond tool use, safety metadata, citations, reasoning blocks,
or provider errors in this step.

### Request round-trip and tool suppression

Change the request-facing signatures without breaking existing callers:

```python
class Client:
    def call(self, max_output_tokens=1024, tools=None):
        ...


class PromptBuilder:
    def to_api_payload(self, max_output_tokens=1024, tools=None):
        ...

    def parse_response(self, response):
        return self.backend.parse_response(response)
```

Each concrete backend similarly accepts:

```python
def to_payload(self, context, max_output_tokens=1024, tools=None):
    selected_tools = self.to_tools(context.tools) if tools is None else tools
    ...
```

The default path is backward-compatible. The explicit empty list is used only
to ensure that the terminal wrap-up cannot request more tools.

OpenAI, Gemini, Ollama, and Ollama Cloud also need a small private helper that
rebuilds an assistant wire message from either normalized blocks or a legacy
plain string. Preserve the original content-block order for Gemini. For
OpenAI and both Ollama variants, join text blocks in order and emit tool calls
in their original relative tool-call order.

### Task limits

Extend the existing `Task` class:

```python
class Task:
    DEFAULT_MAX_ITERATIONS = 25
    DEFAULT_MAX_OUTPUT_TOKENS = 1024

    def max_iterations(self, settings):
        return self._integer_setting(
            settings,
            "max_iterations",
            self.DEFAULT_MAX_ITERATIONS,
        )

    def max_output_tokens(self, settings):
        return self._integer_setting(
            settings,
            "max_output_tokens",
            self.DEFAULT_MAX_OUTPUT_TOKENS,
        )
```

Keep these as methods on the existing `PLAYER` task object. Missing settings
use the defaults; configured numeric strings are accepted through `int`;
invalid values raise `ValueError` or `TypeError`.

### `Agent`

Add `boukensha/agent.py` with the same public surface and constants as Ruby:

```python
class Agent:
    MAX_ITERATIONS = 25
    WRAP_UP_OUTPUT_TOKENS = 400
    WRAP_UP_DIRECTIVE = (
        "You have reached your action limit for this turn. "
        "Do not call any more tools.\n"
        "Briefly summarize what you accomplished, what is still unfinished, "
        "and the\nsingle next action you would take."
    )

    def __init__(
        self,
        *,
        context,
        registry,
        builder,
        client,
        task_settings=None,
        max_iterations=None,
        max_output_tokens=None,
    ):
        ...

    def run(self):
        ...
```

Constructor resolution:

1. An explicit `max_iterations` wins and is converted with `int`.
2. Otherwise, when `task_settings is not None` and the task exposes
   `max_iterations`, use the task value.
3. Otherwise use `Agent.MAX_ITERATIONS`.
4. An explicit `max_output_tokens` wins without extra conversion, matching
   Ruby.
5. Otherwise, when task settings and a task method are available, use the task
   value.
6. Otherwise retain `None`, allowing the client's default on normal calls.

The work loop should be structurally small:

```text
threshold reached? ── yes ──> append directive
       │                       call once with tools=[]
       no                      return wrap-up/fallback text
       │
increment and call model
       │
normalize response
       │
tool_use? ── yes ──> store assistant blocks
       │             dispatch every tool
       │             store every result
       │             repeat
       no
       │
return concatenated text
```

Suggested private helpers mirror the Ruby responsibilities:

- resolve iteration and output-token settings
- test whether the positive threshold has been reached
- build normal per-call options
- perform the single wrap-up call
- build fallback text
- extract normalized text blocks
- dispatch and record normalized tool-use blocks

Do not use `LoopError` at the threshold. Do not allow wrap-up to recurse into
`run`, and do not handle tool calls returned by wrap-up because tools were
explicitly disabled.

### Package exports

Update top-level `boukensha/__init__.py` to retain every step-4 export and add
`Agent` and `LoopError`:

```python
from .agent import Agent
from .errors import ApiError, LoopError, UnknownToolError, UnsupportedModelError
```

Include both names in `__all__`. Backend and task package exports do not
change.

## README / example plan

### README

Rewrite `week1_baseline/python/05_agent_loop/README.md` around the loop delta:

- explain the
  `request -> normalize -> dispatch -> record result -> repeat` flow
- document `Agent.run()` and the normalized dictionary shape
- explain why normalization and reverse serialization belong to backends
- document real versus name-derived tool-call IDs by provider
- emphasize that the assistant tool-use message precedes tool-result messages
- state that every tool call in a response is dispatched synchronously
- document `tasks.player.max_iterations` and `max_output_tokens`, including
  defaults
- explain the positive iteration threshold, the extra tools-disabled wrap-up
  call, the 400-token override, and fallback behavior
- retain the provider/configuration table and step-4 HTTP/retry context only as
  concise carry-forward information
- show Python syntax and the final Python output format
- make clear that the example performs multiple live, potentially billable
  requests and lets the model select paths for real file-reading tools
- provide the correct wrapper command:
  `./week1_baseline/python/bin/05_agent_loop`

Retain useful teaching intent from the Ruby README, but correct stale paths,
stale iteration output, Ruby syntax, and claims that describe files introduced
before step 5.

### Example flow

Rewrite `examples/example.py` iteratively from the step-4 live example:

1. Preserve setting `BOUKENSHA_DIR` before constructing `Config`.
2. Preserve task prompt resolution, provider/model selection, and the same
   five backend branches.
3. Set `base_dir` to the standalone Python `05_agent_loop` snapshot so
   model-provided relative paths resolve consistently regardless of the
   caller's working directory.
4. Construct `Context`, `Registry`, `PromptBuilder`, and `Client`, then create
   `Agent` with `task_settings=player_settings`.
5. Register `read_file` and `list_directory` against `base_dir`. Preserve the
   Ruby-visible tool names, descriptions, and required string `path` schema.
6. Make `read_file` read UTF-8 text. Make `list_directory` omit hidden entries
   and join names with `", "`, matching the step-5 example.
7. Replace the step-4 question with:
   `"Read the README.md file and summarise what this MUD player assistant framework can do."`
8. Print the step-5 heading, config, provider, model, resolved max iterations,
   and resolved max output tokens.
9. Replace direct `client.call()` and raw JSON printing with `agent.run()` and
   a `=== FINAL RESPONSE ===` section.

The example should not catch `ApiError`, `UnknownToolError`, file-system
errors, or provider parse errors. Failures remain visible in this teaching
snapshot. Matching Ruby, anchoring relative paths is not a security boundary:
absolute paths and `..` can escape `base_dir`. Document that limitation rather
than claiming the example is sandboxed.

Add `week1_baseline/python/bin/05_agent_loop` by following the step-4 Python
wrapper: change into the standalone step-5 directory and run
`python3 examples/example.py`. Make it executable.

## Iterative implementation and validation

### Iteration 1 — Normalize raw responses

1. Add `parse_response` to Anthropic, OpenAI, Gemini, Ollama, and Ollama Cloud.
2. Add `PromptBuilder.parse_response`.
3. Validate raw text-only, tool-only, mixed text/tool, missing-content, and
   multiple-tool-call fixtures for each provider.
4. Confirm the output always uses the common string-keyed shape.

Do not add `Agent` yet. At the end of this iteration, step 5 should still run
the copied one-shot example.

### Iteration 2 — Round-trip assistant tool calls

1. Teach OpenAI, Gemini, Ollama, and Ollama Cloud to serialize normalized
   assistant content stored in history.
2. Preserve legacy assistant strings as text.
3. Feed each parser's normalized output into a context and build the next
   provider request.
4. Assert names, arguments, real/synthetic IDs, text, and provider roles
   survive the parse/store/rebuild cycle.

This is the critical seam: do not proceed until a tool request can be replayed
immediately before its matching tool result.

### Iteration 3 — Thread controls through the request path

1. Add `tools=None` to every backend payload method, the builder, and the
   client.
2. Assert omitted/`None` tools serialize registered schemas and `tools=[]`
   serializes an empty list for all providers.
3. Add task defaults and integer-backed accessors.
4. Add and export `LoopError`, while keeping it unused.
5. Re-run the step-4 client-focused checks against the copied step-5 client to
   prove transport behavior did not change.

### Iteration 4 — Add the bounded agent

1. Implement settings precedence and the normal end-turn path.
2. Implement single and multiple tool dispatch with ordered context mutation.
3. Implement repeated model calls.
4. Implement the positive iteration threshold and exactly one wrap-up call.
5. Implement empty-text and `ApiError` fallback paths.
6. Add `Agent` to the package exports.

Use fake clients/builders and ordinary callables. Agent unit checks must not
access the network or sleep.

### Iteration 5 — Finish the standalone snapshot

1. Rewrite the example to use `Agent`.
2. Rewrite the README around step 5.
3. Add and make executable the Python wrapper.
4. Run syntax/import checks and focused offline assertions.
5. Only when credentials and network access are intentionally available, run
   the wrapper once and inspect the full multi-call turn.
6. Re-run step 4 to confirm the prior standalone snapshot remains unaffected.

## Checks to run after the port

1. Compile/import every step-5 Python module and confirm every step-4 public
   export remains available alongside `Agent` and `LoopError`.
2. Verify Anthropic preserves content blocks, maps only exact tool use to the
   tool stop reason, and safely handles missing content.
3. Verify OpenAI parses JSON arguments, preserves provider IDs, handles
   multiple calls, and surfaces malformed argument JSON.
4. Verify Gemini preserves part order and maps function names to synthetic
   IDs.
5. Verify Ollama and Ollama Cloud omit empty text, preserve non-empty text, and
   map function names to synthetic IDs.
6. For every provider, round-trip a normalized assistant response containing
   both text and multiple tool calls into the next request payload.
7. Assert `tools=None` uses registered schemas while `tools=[]` disables tools
   at the backend, builder, and client boundaries.
8. Assert missing task settings resolve to `25` iterations and `1024` output
   tokens, numeric strings convert, explicit agent values win, and invalid
   configured integers fail visibly.
9. Assert an immediate end turn makes one client call and returns all text
   blocks concatenated in order.
10. Assert one tool-use response stores the assistant message first, dispatches
    every tool in order, stores stringified results with matching IDs, and then
    makes the next model call.
11. Assert multiple loop iterations forward the configured normal
    `max_output_tokens`.
12. With `max_iterations=1`, assert one normal call plus exactly one wrap-up
    call; the second call uses `tools=[]` and `max_output_tokens=400`.
13. Assert `max_iterations=0` and a negative value disable threshold checks in
    a finite fake-response sequence.
14. Assert a non-empty wrap-up returns model text, empty wrap-up text returns
    fallback text, and wrap-up `ApiError` returns the same fallback.
15. Assert normal-call `ApiError`, `UnknownToolError`, callback failures, and
    parse errors are not swallowed.
16. Assert progress output contains `[iteration N/LIMIT]`, each tool name and
    arguments, and no more than the Ruby-equivalent 61-character result
    preview.
17. Confirm all offline checks use fake raw responses and patched clients; no
    test should make a provider request.
18. Run `./week1_baseline/python/bin/05_agent_loop` only with intentional
    credentials/network access and confirm the agent reads the snapshot README
    through tool calls before returning final text.
19. Re-run `./week1_baseline/python/bin/04_api_client` to confirm the previous
    standalone snapshot remains unchanged.

If the repository has no automated test suite for these snapshots, implement
the checks as focused `python3` assertions using `unittest.mock` and
`contextlib.redirect_stdout` rather than introducing a test framework.

## Explicitly defer for later steps

- Streaming and incremental JSON/event parsing
- Async model calls, parallel tool execution, or concurrency
- Persistent sessions, checkpoints, replay logs, or resuming an interrupted
  loop
- Human approval gates, tool allowlists, filesystem sandboxing, or permission
  policies
- Tool argument schema validation beyond provider-generated JSON parsing
- Automatic retries or recovery for tool callbacks, unknown tools, response
  parsing, or normal agent-loop failures
- Returning partial text emitted alongside tool calls to the user
- Rich response/message classes in place of the normalized dictionaries
- Usage, token-cost, context-window, latency, or iteration telemetry
- Context trimming, summarization, compaction, or token-budget enforcement
- Cancellation, wall-clock deadlines, and a total limit that includes wrap-up
- Configurable wrap-up prompts or wrap-up output-token counts
- Changes to the step-4 HTTP retry, TLS, timeout, or error policy
- Dynamic model discovery or changes to backend model metadata
- General config/task/registry changes not required by Ruby `05_agent_loop`
