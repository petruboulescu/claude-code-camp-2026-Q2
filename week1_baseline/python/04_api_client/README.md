# The API Client

The API client takes the payload assembled by `PromptBuilder`, sends one HTTP
POST, and returns the provider's raw decoded JSON response. There is no tool
loop yet; this step only proves that a complete request can make the round
trip.

```text
PromptBuilder
      |
      v
Client
      |
      v
POST to provider API
      |
      v
Raw JSON response
```

## What changed

| File | Change |
|---|---|
| `boukensha/client.py` | Sends the request, retries transient failures, and decodes JSON |
| `boukensha/errors.py` | Adds `ApiError` for transport and HTTP failures |
| `boukensha/__init__.py` | Exports `Client` and `ApiError` |
| `examples/example.py` | Sends a live request and prints the raw response |
| `prompts/system.md` | Uses the step-4 Boukensha player prompt |

All prompt serialization, backend selection, model validation, model metadata,
and registry behavior are carried forward unchanged from step 3.

## Client

```python
builder = PromptBuilder(context, backend)
client = Client(builder)
response = client.call(max_output_tokens=1024)
```

`Client.call`:

1. gets the URL, headers, and JSON-ready payload from `PromptBuilder`
2. sends a UTF-8 JSON POST
3. accepts any HTTP 2xx response
4. returns the value produced by `json.loads`

The response is intentionally not normalized. Anthropic, Gemini, OpenAI, and
the two Ollama backends each return their native response shape. Extracting
assistant text and tool calls belongs to step 5.

## Retries and errors

The client retries transient connection, timeout, TLS, socket, and EOF
failures. It also retries HTTP statuses `408`, `409`, `429`, `500`, `502`,
`503`, and `504`.

There are at most four attempts: the initial request and three retries. Delays
use deterministic exponential backoff of `0.5`, `1.0`, and `2.0` seconds.

A final transport failure or non-2xx response raises `ApiError`. HTTP errors
include the status and response body. A malformed JSON document in an otherwise
successful response raises the standard `json.JSONDecodeError`.

## No new dependency

The client uses Python's standard `urllib.request` and `json` modules. HTTPS
uses Python's verified system TLS configuration by default. A local Ollama
backend continues to use plain HTTP at its configured host.

## Raw response examples

Anthropic can return:

```json
{
  "id": "msg_01XY",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Sure, let me read that file."}
  ],
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 42, "output_tokens": 18}
}
```

Ollama can return:

```json
{
  "model": "llama3.2",
  "message": {
    "role": "assistant",
    "content": "Sure, let me read that file."
  },
  "done_reason": "stop",
  "done": true
}
```

When a model requests a tool, these shapes differ again. This step returns
that response unchanged and does not dispatch the tool.

## Configuration

The selected task still owns its provider and model:

```yaml
tasks:
  player:
    provider: anthropic
    model: claude-haiku-4-5
    prompt_override:
      system: true
```

When `prompt_override.system` is true, Boukensha reads
`.boukensha/prompts/player/system.md`. Otherwise it uses this snapshot's
`prompts/system.md`.

API-backed providers require their matching environment variable:

- Anthropic: `ANTHROPIC_API_KEY`
- Gemini: `GEMINI_API_KEY`
- OpenAI: `OPENAI_API_KEY`
- Ollama Cloud: `OLLAMA_API_KEY`
- local Ollama: no API key

## Run the example

```sh
./week1_baseline/python/bin/04_api_client
```

Unlike step 3, this command makes a live request. The provider must be
reachable, the configured model must be supported, and API-backed providers
need valid credentials. The request may incur provider charges.
