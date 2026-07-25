# Python Port Plan — 04_api_client

Port `week1_baseline/ruby/04_api_client` to
`week1_baseline/python/04_api_client` as the next self-contained Python
snapshot after `week1_baseline/python/03_prompt_builder`.

Current starting point: `week1_baseline/python/04_api_client` has already been
seeded by copying the completed Python `03_prompt_builder` snapshot. This plan
and the implementation are therefore delta only.

This step stays intentionally focused on one HTTP round trip:

- preserve the Python prompt-builder snapshot's behavior, layout, and APIs
  unless Ruby step 4 explicitly changes them
- add a small `Client` that sends the payload produced by `PromptBuilder`
- use only Python's standard-library HTTP and JSON modules
- retry the same transient failures and HTTP status codes as the Ruby client
- return the provider's raw decoded JSON response without normalizing it
- update the example from offline payload generation to a live API request
- do not add response objects, tool-call parsing, or an agent loop

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/04_api_client/README.md` | step contract, raw provider response examples, and HTTP-client teaching notes |
| `week1_baseline/ruby/04_api_client/lib/boukensha/client.rb` | new POST client, retry policy, TLS behavior, JSON decoding, and failure messages |
| `week1_baseline/ruby/04_api_client/lib/boukensha/errors.rb` | adds `ApiError` |
| `week1_baseline/ruby/04_api_client/lib/boukensha.rb` | adds the client to the public load surface |
| `week1_baseline/ruby/04_api_client/examples/example.rb` | changes the demo to file tools and a live `Client#call` |
| `week1_baseline/ruby/04_api_client/prompts/system.md` | replaces the step-3 MUD-assistant prompt with the Boukensha player prompt |
| `week1_baseline/ruby/04_api_client/lib/boukensha/tasks/base.rb` | task-setting defensive lookup and corrected `settings.yaml` messages |
| `week1_baseline/ruby/04_api_client/lib/boukensha/config.rb` | confirms the shipped prompt belongs to this standalone step |
| `week1_baseline/ruby/04_api_client/lib/boukensha/{prompt_builder,context,message,registry,tool}.rb` | carried-forward request-building and registry behavior used by the example |
| `week1_baseline/ruby/04_api_client/lib/boukensha/backends/*.rb` | carried-forward payload, header, URL, model validation, and metadata behavior |
| `week1_baseline/ruby/04_api_client/Gemfile` / `Gemfile.lock` | confirms the HTTP client adds no dependency |
| `week1_baseline/ruby/bin/04_api_client` | wrapper entry point |

Also read the completed previous Python port for all carry-forward decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/03_prompt_builder/boukensha/*.py` | existing public types, errors, exports, and `PromptBuilder` API to preserve |
| `week1_baseline/python/03_prompt_builder/boukensha/backends/*.py` | provider payloads, headers, URLs, and model metadata consumed by `Client` |
| `week1_baseline/python/03_prompt_builder/boukensha/tasks/*.py` | existing task configuration and defensive dictionary lookup |
| `week1_baseline/python/03_prompt_builder/examples/example.py` | backend selection and Python example conventions |
| `week1_baseline/python/03_prompt_builder/README.md` | prior step's documented contract |
| `week1_baseline/python/bin/03_prompt_builder` | wrapper-script pattern |

The copied `week1_baseline/python/04_api_client` snapshot is currently
identical to Python step 3. Treat every unchanged file as already migrated;
only add or edit the files named by this plan.

## Behavior to preserve exactly

1. **Prompt construction is unchanged**: `PromptBuilder` and all five
   backends continue to own payloads, headers, endpoints, and model metadata.
   `Client` must not contain provider branches.
2. **The client performs one logical POST** using `builder.url`,
   `builder.headers`, and
   `builder.to_api_payload(max_output_tokens=...)`.
3. **The request body is UTF-8 JSON** and the decoded response is returned as
   the raw Python JSON value. Provider response shapes remain unnormalized.
4. **Successful responses are all HTTP 2xx statuses**, not only `200`.
5. **Retryable HTTP statuses match Ruby exactly**:
   `408`, `409`, `429`, `500`, `502`, `503`, and `504`.
6. **Transient connection failures are retried**. Cover the Python
   equivalents of Ruby's EOF, connection reset/refused, open/read timeout,
   TLS, socket, and timeout errors without catching programming errors or
   `KeyboardInterrupt`.
7. **`MAX_RETRIES = 3` means three retries after the initial request**:
   at most four attempts total.
8. **Backoff is deterministic exponential backoff**:
   `0.5`, `1.0`, and `2.0` seconds before attempts two through four. Do not
   add jitter or honor `Retry-After` in this tutorial step.
9. **Retryable HTTP responses are retried only while retries remain**. A
   retryable response received on the fourth attempt becomes the final
   non-success failure.
10. **Non-retryable non-2xx responses fail immediately** with `ApiError`.
11. **An exhausted transient exception raises `ApiError`** with the attempt
    count, exception type, and original message. Preserve the original
    exception as the Python cause.
12. **A final HTTP failure raises `ApiError`** with the total attempt count,
    status code, and decoded response body so authentication and payload
    errors remain diagnosable.
13. **TLS verification remains enabled by default**. Rely on Python's default
    verified HTTPS context; do not disable certificate checks or hard-code a
    CA path. Local Ollama continues to use plain HTTP through its backend URL.
14. **`ApiError` is dedicated to transport and HTTP failures**. JSON decoding
    errors from a successful but malformed response may remain the standard
    `json.JSONDecodeError`, matching Ruby's unwrapped parser failure.
15. **The example makes a real request** and therefore requires a reachable
    configured provider plus the selected provider's API key. It prints the
    raw decoded response and does not execute requested tools.
16. **Prior snapshots remain standalone and unchanged**. Step 4 must not
    import implementation code from Python step 3.

## Already incorporated from the Ruby step-4 diff

Ruby step 4 makes two small defensive changes in `tasks/base.rb`: it names
`settings.yaml` correctly in errors and returns no value when task settings
are not a hash. The Python step-3 `Task` already uses the correct filename and
checks `isinstance(settings, dict)`. Keep that implementation unchanged rather
than manufacturing a step-4 diff.

Ruby's `config.rb` change is comment/whitespace only, and the Python config
already resolves the prompt directory for its local snapshot. Keep
`boukensha/config.py` unchanged.

## Python-specific decisions

- Use `urllib.request.Request` and `urllib.request.urlopen` so the HTTP call is
  visible and no third-party client is added. Build the request with
  `method="POST"` and `json.dumps(payload).encode("utf-8")`.
- Preserve backend-provided headers. Add no provider-specific headers in
  `Client`; the existing backends already supply `Content-Type` and
  authentication as required.
- Treat `urllib.error.HTTPError` as an HTTP response, not as a transient
  connection exception. Inspect its status and body so retryable statuses can
  follow the same policy as ordinary responses.
- Treat `urllib.error.URLError` and the relevant socket/connection/TLS
  exceptions as transient transport failures. Because `URLError` often wraps
  the lower-level reason, the final `ApiError` should still expose useful
  exception details.
- Decode response and error bodies as UTF-8. Use replacement for undecodable
  bytes in error text so reporting a failed response cannot mask the HTTP
  failure; successful JSON should decode strictly.
- Keep sleeping replaceable for focused tests, either through a small private
  helper or constructor injection with `time.sleep` as the public default.
  Do not expose retry configuration as a new tutorial-facing API.
- Do not add asynchronous I/O, sessions, pooling, streaming, provider SDKs,
  a third-party retry package, request logging, or response normalization.
- Do not add a new explicit timeout unless the Ruby step or repository
  contract specifies one. A timeout policy can be introduced in a later
  transport-hardening step.

## Proposed target layout

```text
week1_baseline/python/04_api_client/
  requirements.txt               # carried forward unchanged
  README.md                       # rewrite for step 4
  boukensha/
    __init__.py                   # add Client and ApiError exports
    client.py                     # new standard-library POST client
    config.py                     # carried forward unchanged
    context.py                    # carried forward unchanged
    errors.py                     # add ApiError
    message.py                    # carried forward unchanged
    prompt_builder.py             # carried forward unchanged
    registry.py                   # carried forward unchanged
    tool.py                       # carried forward unchanged
    backends/                     # all files carried forward unchanged
    tasks/                        # all files carried forward unchanged
  prompts/
    system.md                     # replace with Ruby step-4 prompt
  examples/
    example.py                    # rewrite for a live round trip
week1_baseline/python/bin/04_api_client
```

Each numbered step remains a standalone snapshot; do not import implementation
code from `python/03_prompt_builder`.

## API plan

### `ApiError`

Extend `boukensha/errors.py` without changing the existing exceptions:

```python
class ApiError(Exception):
    pass
```

Use it for final transport failures and non-success HTTP responses. Do not use
it for unsupported models, missing configuration, JSON parse failures, or tool
dispatch.

### `Client`

Add `boukensha/client.py` with a small stateful facade matching Ruby:

```python
class Client:
    RETRYABLE_STATUS_CODES = frozenset({408, 409, 429, 500, 502, 503, 504})
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5

    def __init__(self, builder):
        self.builder = builder

    def call(self, max_output_tokens=1024):
        ...
```

`call` should:

1. Ask the builder for the payload, URL, and headers.
2. JSON-encode the payload and create one POST request.
3. Attempt the request up to four times.
4. Return `json.loads(...)` for any 2xx response.
5. Retry eligible status responses and transient exceptions with exponential
   delays.
6. Raise `ApiError` when a final transport or HTTP failure is reached.

Private helpers may separate:

- request construction
- status extraction and success/retry classification
- response-body reading and decoding
- transient-exception classification
- retry-delay calculation and sleeping
- consistent singular/plural attempt wording

Keep these helpers transport-oriented. They must not inspect provider payloads
or response schema.

When `HTTPError` supplies the failed response, read its body only when that
attempt is final. A retryable error response should be closed/discarded before
sleeping. Normal successful responses should be used as context managers so
resources are closed promptly.

### Package exports

Update top-level `boukensha/__init__.py` to retain every step-3 export and add
`Client` and `ApiError`:

```python
from .client import Client
from .errors import ApiError, UnknownToolError, UnsupportedModelError
```

Include both new names in `__all__`. Backend package exports do not change.

## README / example plan

### README

Rewrite `week1_baseline/python/04_api_client/README.md` around the HTTP-client
delta:

- explain the `PromptBuilder -> Client -> POST -> raw JSON` flow
- document `Client.call(max_output_tokens=1024)`
- show that provider configuration and model validation are carried forward
- explain the no-new-dependency standard-library choice
- document success handling, `ApiError`, transient retries, the exact retry
  statuses, four-attempt maximum, and exponential delays
- explain verified HTTPS and plain HTTP for local Ollama without
  Ruby-specific OpenSSL/CA-path instructions
- include concise Anthropic and Ollama raw response examples
- state that response/tool-call normalization is deferred to step 5
- make clear that the example performs a live, potentially billable request
- provide the Python wrapper command:
  `./week1_baseline/python/bin/04_api_client`

Retain useful teaching intent from the Ruby README, but correct stale paths,
typos, output commands, and Ruby-specific syntax rather than copying them.

### Example flow

Rewrite `examples/example.py` to:

1. Set `BOUKENSHA_DIR` before constructing `Config`.
2. Read `player` settings and resolve its system prompt from the user and
   shipped prompt directories.
3. Create `Context` and `Registry`.
4. Register `read_file` with the required string `path` parameter and a
   function that reads UTF-8 text from that path.
5. Register `list_directory` with the required string `path` parameter and a
   function that returns non-hidden entry names joined by newlines.
6. Add only the Ruby example's user message:
   `"What files are in the current directory?"`
7. Select the same five backends from the configured provider and model.
8. Read only the selected provider's required environment variable;
   local Ollama needs none.
9. Raise a clear `ValueError` for an unsupported provider.
10. Construct `PromptBuilder` and then `Client`.
11. Print the step heading, config, provider, model, and destination URL.
12. Call `client.call()` and pretty-print the returned raw JSON.

Keep file-tool callbacks registered because their schemas are sent to the
model, but do not dispatch them in this step. Use Python APIs (`Path.read_text`
or `open`, and directory iteration) while preserving the Ruby-visible tool
names, descriptions, and parameter schema. Do not silently catch `ApiError`;
the failure should remain visible in this minimal example.

## Implementation order

1. **Keep the copied prompt-builder snapshot as the baseline**.
   Do not rewrite the builder, backends, context, registry, task classes,
   configuration, requirements, or other carried-forward files.
2. **Add `ApiError` and `Client`**.
   Implement request construction, raw JSON decoding, retry classification,
   deterministic backoff, and final error reporting.
3. **Expand package exports**.
   Add `Client` and `ApiError` without dropping any step-3 symbol.
4. **Update the shipped system prompt**.
   Port the Ruby step-4 Boukensha player prompt exactly.
5. **Rewrite the example**.
   Switch from offline payload printing to file-tool registration and one live
   client call.
6. **Rewrite the README**.
   Document the Python client, retry behavior, raw responses, and live-run
   requirements.
7. **Add `week1_baseline/python/bin/04_api_client`**.
   Follow the existing Python wrapper style and make it executable.

## Checks to run after the port

1. Run syntax/import checks for every step-4 Python module.
2. Confirm every step-3 public export remains available and `Client` plus
   `ApiError` are exported from `boukensha`.
3. With a fake builder and mocked `urlopen`, assert the request is POST,
   headers come from the builder, the body is UTF-8 JSON, and
   `max_output_tokens` reaches `builder.to_api_payload`.
4. Assert representative `200`, `201`, and `204` handling. For an empty `204`,
   preserve normal JSON-decoder behavior rather than inventing a response.
5. Assert each retryable status is retried, a non-retryable `4xx` is not, and
   the maximum is four total attempts.
6. Assert retry delays are exactly `[0.5, 1.0, 2.0]` without actually sleeping
   in tests.
7. Assert representative connection refused/reset, timeout, `URLError`, EOF,
   and TLS failures retry and eventually raise `ApiError` chained from the
   final exception.
8. Assert final HTTP errors include attempt count, status, and response body.
9. Assert a successful malformed JSON response raises `JSONDecodeError`.
10. Confirm client tests never access the network; use standard-library mocks
    or a tiny local HTTP server.
11. Run `./week1_baseline/python/bin/04_api_client` once against the selected
    configured provider and confirm it prints decoded JSON. This is the only
    check that should make an external/provider request and should be run only
    when credentials and network access are intentionally available.
12. Re-run `./week1_baseline/python/bin/03_prompt_builder` to confirm the prior
    standalone snapshot remains unaffected.

If the repository has no automated test suite for these snapshots, implement
the checks as focused `python3` assertions using `unittest.mock` rather than
introducing a test framework or an HTTP dependency.

## Explicitly defer for later steps

- Normalizing provider response shapes
- Extracting assistant text, stop reasons, usage, or tool calls
- Constructing tool-call request objects or dispatching registered tools
- Feeding tool results back to the model
- The multi-turn agent loop
- Streaming and incremental JSON/event parsing
- Async requests, concurrency, connection pooling, or persistent sessions
- Configurable retry counts, backoff, jitter, and `Retry-After`
- Explicit connect/read timeouts and cancellation
- Provider SDKs and third-party HTTP/retry libraries
- Request/response logging, redaction, telemetry, and token-cost accounting
- Dynamic model discovery or changes to backend model metadata
- Any change to the task/config/registry architecture not required by Ruby
  `04_api_client`
