# The Prompt Builder

LLM access, cost, and quality change frequently, so Boukensha needs to switch
between the model families that drive its agent loop:

- Anthropic
- OpenAI
- Gemini
- local Ollama
- Ollama Cloud

`PromptBuilder` serializes a `Context` into the exact plain-dictionary format
expected by the selected API. It delegates to a backend but never calls the
API; this step only prepares payloads, headers, and URLs.

Task-based configuration is carried forward from the registry step. The
`player` task owns its provider, model, and prompt override settings, while the
context records the task whose prompt is being built.

## New Python modules

| Module | Purpose |
|---|---|
| `boukensha/prompt_builder.py` | Delegates serialization to the active backend |
| `boukensha/backends/base.py` | Model validation, metadata, and cost estimates |
| `boukensha/backends/anthropic.py` | Anthropic Messages API format |
| `boukensha/backends/gemini.py` | Gemini `generateContent` format |
| `boukensha/backends/ollama.py` | Local Ollama chat format |
| `boukensha/backends/ollama_cloud.py` | Authenticated Ollama Cloud format |
| `boukensha/backends/openai.py` | OpenAI Chat Completions format |

The registry, context, messages, tools, tasks, and prompt resolution are copied
forward unchanged.

## How it works

```text
Context (Python objects)
        ↓
PromptBuilder
        ↓
Backend (Anthropic, OpenAI, Gemini, Ollama, or Ollama Cloud)
        ↓
API payload (plain dictionaries and lists)
        ↓
json.dumps(...)
```

`PromptBuilder` exposes:

| Member | Description |
|---|---|
| `to_messages()` | Serializes context messages for the backend |
| `to_tools()` | Serializes registered tool schemas |
| `to_api_payload()` | Builds the complete request body |
| `headers` | Returns the provider's HTTP headers |
| `url` | Returns the provider's endpoint URL |

## Provider differences

Anthropic and Gemini place the system prompt at the payload's top level.
OpenAI and both Ollama variants prepend a system message.

```json
// Anthropic
{"system": "You are a MUD player assistant.", "messages": []}

// Gemini
{"systemInstruction": {"parts": [{"text": "You are a MUD player assistant."}]}, "contents": []}

// OpenAI / Ollama
{"messages": [{"role": "system", "content": "You are a MUD player assistant."}]}
```

Anthropic wraps tool results as user content. OpenAI uses a `tool` message with
`tool_call_id`, Ollama uses `tool_name`, and Gemini uses a
`functionResponse` part. Gemini also maps the assistant role to `model`.

Tool definitions differ in the same way:

- Anthropic uses `input_schema`.
- OpenAI and Ollama use a `type: function` envelope.
- Gemini uses `functionDeclarations`.

Every declared parameter is placed in the schema's `required` list. Tool
descriptions and schemas are all the model sees; Python callables stay inside
Boukensha.

## Model validation and metadata

Each backend owns a static supported-model table. Construction with an unknown
model raises `UnsupportedModelError` rather than silently accepting a typo.
Backends expose:

- `model` and `model_info`
- `context_window`
- `input_token_cost_per_million`
- `output_token_cost_per_million`
- `usage_unit` and optional `usage_level`
- `estimate_cost(input_tokens=..., output_tokens=...)`

Local Ollama models report `0.0` token API cost. Ollama Cloud pricing is
plan/usage based, so its token prices and cost estimate are `None`.

Prices and model details in this tutorial snapshot are static data current as
of June 16, 2026. Review them whenever the supported model set changes.

## Run the example

The configured provider may require its API key in the environment:
`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, or
`OLLAMA_API_KEY`. Local Ollama requires no key.

```sh
./week1_baseline/python/bin/03_prompt_builder
```

The example prints indented JSON. It does not connect to a provider or send a
request.

## Considerations

The conversation remains stateless: a future API call will include the entire
context history. This step does not count tokens, truncate context, execute
model-selected tools, parse responses, or perform HTTP transport.
