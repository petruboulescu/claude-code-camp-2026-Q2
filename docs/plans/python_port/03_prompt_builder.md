# Python Port Plan — 03_prompt_builder

Port `week1_baseline/ruby/03_prompt_builder` to
`week1_baseline/python/03_prompt_builder` as the next self-contained Python
snapshot after `week1_baseline/python/02_the_registry`.

Current starting point: `week1_baseline/python/03_prompt_builder` has already
been seeded by copying the completed Python `02_the_registry` snapshot. This
plan and the implementation are therefore delta only.

This step stays intentionally focused on serialization:

- preserve the Python registry snapshot's behavior, layout, and APIs unless
  Ruby step 3 explicitly changes them
- add `PromptBuilder` as a small facade over provider-specific serializers
- add Anthropic, Gemini, Ollama, Ollama Cloud, and OpenAI backends
- validate configured model names and expose the Ruby model metadata/cost API
- build plain Python dictionaries and lists ready for JSON encoding
- do not make HTTP requests or add provider SDK dependencies

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/03_prompt_builder/README.md` | step contract, provider differences, model metadata, and example payloads |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha.rb` | expanded top-level require/export surface |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/prompt_builder.rb` | new facade that delegates serialization, headers, and URL to a backend |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/backends/base.rb` | shared model validation, metadata accessors, and cost estimation |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/backends/anthropic.rb` | Anthropic messages, tools, payload, headers, endpoint, and model table |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/backends/gemini.rb` | Gemini `generateContent` serialization and model table |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/backends/ollama.rb` | local Ollama serialization, configurable host, and model table |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/backends/ollama_cloud.rb` | authenticated Ollama Cloud serialization and usage metadata |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/backends/openai.rb` | OpenAI Chat Completions serialization and model table |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/errors.rb` | adds `UnsupportedModelError` |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/config.rb` | adds the shipped `PROMPTS_DIR` path |
| `week1_baseline/ruby/03_prompt_builder/examples/example.rb` | selects a backend from task config and prints the generated payload |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/{context,message,registry,tool}.rb` | carried-forward data and registry behavior consumed by serializers |
| `week1_baseline/ruby/03_prompt_builder/lib/boukensha/tasks/{base,player}.rb` | carried-forward task config and prompt resolution |
| `week1_baseline/ruby/03_prompt_builder/prompts/system.md` | shipped default system prompt |
| `week1_baseline/ruby/03_prompt_builder/Gemfile` / `Gemfile.lock` | confirms no provider SDK or HTTP client is added |

Also read the completed previous Python port for all carry-forward decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/02_the_registry/boukensha/*.py` | existing Python types, registry API, errors, and exports to preserve |
| `week1_baseline/python/02_the_registry/boukensha/tasks/*.py` | existing `Task`/`PLAYER` API and prompt resolution |
| `week1_baseline/python/02_the_registry/examples/example.py` | existing Python example conventions |
| `week1_baseline/python/02_the_registry/README.md` | prior step's documented contract |
| `week1_baseline/python/bin/02_the_registry` | wrapper-script pattern |

The copied `week1_baseline/python/03_prompt_builder` snapshot is currently
identical to Python step 2. Treat every unchanged file as already migrated;
only add or edit the files named by this plan.

## Behavior to preserve exactly

1. **Registry behavior is unchanged**: tool registration, context-owned tool
   storage, dispatch, and `UnknownToolError` remain as implemented in Python
   step 2.
2. **Context and message shapes are sufficient already**: messages have
   `role`, `content`, and optional `tool_use_id`; context has `system`,
   `messages`, and `tools`.
3. **PromptBuilder only prepares requests**. It delegates serialization,
   headers, and endpoint selection; it never performs an HTTP request.
4. **Every backend validates its model during construction** and raises the
   new dedicated `UnsupportedModelError` for unknown models.
5. **Model metadata mirrors Ruby step 3**, including context windows, static
   per-million-token prices, usage units, and Ollama Cloud usage levels.
6. **Cost estimation mirrors Ruby**: token-priced backends return the
   proportional floating-point cost; local Ollama returns `0.0`; Ollama Cloud
   returns `None` because its prices are not token based.
7. **System prompt placement is provider-specific**:
   Anthropic uses `system`, Gemini uses `systemInstruction`, and OpenAI/Ollama
   prepend a `system` message.
8. **Message serialization is provider-specific**:
   Gemini maps assistant messages to `model`; tool results use Anthropic
   `tool_result`, Gemini `functionResponse`, OpenAI `tool_call_id`, or Ollama
   `tool_name`.
9. **Tool schemas are provider-specific**:
   Anthropic uses `input_schema`; OpenAI and both Ollama backends use a
   `type: function` envelope; Gemini uses `functionDeclarations`.
10. **All tool parameter names are required**, matching Ruby's
    `tool.parameters.keys` behavior.
11. **Provider headers and URLs match Ruby step 3**, including local Ollama's
    configurable host and Gemini's model-specific URL.
12. **The example is offline**: it may require the selected provider's API key
    to construct headers, but it only prints JSON and sends nothing.

## Python-specific decisions

- Use plain `dict`, `list`, and string values so `json.dumps(...)` can encode
  every payload directly. Preserve the Ruby API's wire key casing exactly
  (`systemInstruction`, `functionDeclarations`, `generationConfig`, and so
  on).
- Represent Ruby symbols as their wire-format strings. Message roles are
  already strings in the copied Python snapshot.
- Keep model tables as class-level dictionaries and expose them without
  mutating the Ruby-derived tutorial data.
- Use Python keyword-only constructors where they make provider requirements
  clear: API-backed providers require `api_key` and `model`; local Ollama
  requires `model` and defaults `host` to `http://localhost:11434`.
- Give every backend one internally consistent serialization contract.
  In particular, the builder should pass the full `Context` to message
  serialization (or otherwise supply both `system` and `messages`). This avoids
  copying the Ruby facade's arity mismatch, where `PromptBuilder#to_messages`
  passes only messages although OpenAI and Ollama serializers also require the
  system prompt.
- Keep `max_output_tokens=1024` on the public payload-building API. Anthropic
  maps it to `max_tokens`, Gemini to `generationConfig.maxOutputTokens`, and
  OpenAI to `max_completion_tokens`; the Ruby Ollama payloads intentionally do
  not include it.
- Do not introduce abstract-framework machinery, provider SDKs, HTTP clients,
  schema validation, retries, environment loading inside backends, or async
  APIs.

## Proposed target layout

```text
week1_baseline/python/03_prompt_builder/
  requirements.txt               # carried forward unchanged
  README.md                       # rewrite for step 3
  boukensha/
    __init__.py                   # export builder, backends, and new error
    config.py                     # copied baseline already includes PROMPTS_DIR
    context.py                    # carried forward unchanged
    errors.py                     # add UnsupportedModelError
    message.py                    # carried forward unchanged
    prompt_builder.py             # new facade
    registry.py                   # carried forward unchanged
    tool.py                       # carried forward unchanged
    backends/
      __init__.py                 # public backend exports
      base.py                     # shared model metadata behavior
      anthropic.py
      gemini.py
      ollama.py
      ollama_cloud.py
      openai.py
    tasks/
      __init__.py                 # carried forward unchanged
      base.py                     # carried forward unchanged
      player.py                   # carried forward unchanged
  prompts/
    system.md                     # carried forward unchanged
  examples/
    example.py                    # rewrite to print a provider payload
week1_baseline/python/bin/03_prompt_builder
```

Each numbered step remains a standalone snapshot; do not import implementation
code from `python/02_the_registry`.

## API plan

### `UnsupportedModelError`

Extend `boukensha/errors.py` without changing `UnknownToolError`:

```python
class UnsupportedModelError(Exception):
    pass
```

An invalid model should identify the backend, rejected model, and sorted
supported model names, following the Ruby error's intent.

### `Backend`

Add a small shared base class in `boukensha/backends/base.py`:

```python
class Backend:
    MODELS = None

    @classmethod
    def models(cls) -> dict[str, dict]:
        ...

    @classmethod
    def model_info_for(cls, model: str) -> dict | None:
        ...

    @classmethod
    def validate_model(cls, model: str) -> str:
        ...

    @property
    def model_info(self) -> dict:
        ...

    @property
    def context_window(self) -> int:
        ...

    def estimate_cost(self, *, input_tokens: int, output_tokens: int) -> float | None:
        ...
```

The base class should also expose
`input_token_cost_per_million`, `output_token_cost_per_million`,
`usage_unit`, and optional `usage_level`. A protected configuration helper can
store the normalized model and its metadata after validation.

If a concrete backend omits `MODELS`, accessing the model table should raise
`NotImplementedError`. Unknown models raise `UnsupportedModelError`.

### Provider backends

Implement five concrete serializers with the exact Ruby model tables:

| Backend | Constructor | URL | Important payload differences |
|------|------|------|------|
| `Anthropic` | `api_key`, `model` | `https://api.anthropic.com/v1/messages` | top-level `system`, `max_tokens`, Anthropic tool/result shapes |
| `Gemini` | `api_key`, `model` | model-specific Google `generateContent` URL | `systemInstruction`, `contents`, camelCase generation/tool fields |
| `Ollama` | `model`, optional `host` | `<host>/api/chat` | system message, `stream: False`, no auth |
| `OllamaCloud` | `api_key`, `model` | `https://ollama.com/api/chat` | Ollama shape plus bearer auth and cloud usage metadata |
| `OpenAI` | `api_key`, `model` | `https://api.openai.com/v1/chat/completions` | system message, `max_completion_tokens`, bearer auth |

Each backend needs:

- `to_messages(...)`
- `to_tools(tools)`
- `to_payload(context, max_output_tokens=1024)`
- a `headers` property
- a `url` property

Preserve empty collections rather than omitting fields: Gemini `to_tools`
returns `[]` when no tools exist, and all payloads include their `tools` field
as Ruby does.

For OpenAI and both Ollama variants, a small shared helper is acceptable only
if it reduces literal duplication without obscuring the provider-specific
tool-result identifier and authentication differences. Keep the five public
backend classes and their step-local model tables explicit.

### `PromptBuilder`

Add `boukensha/prompt_builder.py` as a thin facade:

```python
class PromptBuilder:
    def __init__(self, context: Context, backend: Backend):
        self.context = context
        self.backend = backend

    def to_messages(self) -> list[dict]:
        ...

    def to_tools(self) -> list[dict]:
        ...

    def to_api_payload(self, max_output_tokens: int = 1024) -> dict:
        ...

    @property
    def headers(self) -> dict[str, str]:
        ...

    @property
    def url(self) -> str:
        ...
```

The builder must not duplicate provider conditionals. Backend selection occurs
outside it; all five methods simply delegate to the selected backend.

### Package exports

Update `boukensha/backends/__init__.py` to export `Backend`, `Anthropic`,
`Gemini`, `Ollama`, `OllamaCloud`, and `OpenAI`.

Update the top-level `boukensha/__init__.py` to retain every step-2 export and
add `PromptBuilder`, `UnsupportedModelError`, and the backend classes. This
keeps the example concise while preserving direct
`boukensha.backends` imports.

## README / example plan

### README

Rewrite `week1_baseline/python/03_prompt_builder/README.md` around the prompt
builder delta:

- explain that `PromptBuilder` serializes context but does not call APIs
- document the five supported provider families and backend selection
- show system prompts, normal messages, tool results, and tool definitions in
  each provider's wire format
- document model validation and metadata/cost accessors
- state that prices are static tutorial data current as of June 16, 2026
- describe Python-specific dictionaries, string roles, `None` cloud costs, and
  `json.dumps`
- provide the Python wrapper command and note that no network request occurs

Keep the teaching content from the Ruby README, but fix paths and names for the
Python package rather than copying Ruby syntax.

### Example flow

Rewrite `examples/example.py` to:

1. Set `BOUKENSHA_DIR` before constructing `Config`.
2. Read the `player` task settings and resolve its system prompt using both the
   user prompts directory and `Config.PROMPTS_DIR`.
3. Create a `Context` and `Registry`.
4. Register `look` with no parameters.
5. Register `move` with the parameter description added by Ruby step 3.
6. Add the user, assistant, and `tool_result` messages from the Ruby example.
7. Read provider and model through `PLAYER`.
8. Select the matching backend from an explicit provider-to-class branch.
9. Read only the selected backend's required API key with a clear missing-key
   error; local Ollama needs none.
10. Raise a clear `ValueError` for an unsupported provider name.
11. Construct `PromptBuilder`, then print config, provider, model, and
    `json.dumps(builder.to_api_payload(), indent=2)`.

The example must not dispatch tools or call an external service; those belong
to the preceding and future steps respectively.

## Implementation order

1. **Keep the copied registry snapshot as the baseline**.
   Do not rewrite `Context`, `Message`, `Registry`, `Tool`, task classes,
   prompts, or requirements.
2. **Extend errors and add the backend base**.
   Introduce model validation, metadata accessors, and cost estimation.
3. **Add all five provider backends**.
   Port exact model tables, message/tool serialization, payloads, headers, and
   URLs.
4. **Add `PromptBuilder`**.
   Keep it as delegation only and use a consistent context-aware message
   contract.
5. **Expand package exports**.
   Add the backend package exports and new top-level symbols without dropping
   registry symbols.
6. **Rewrite the example and README**.
   Demonstrate configured backend selection and offline payload generation.
7. **Add `week1_baseline/python/bin/03_prompt_builder`**.
   Follow the existing Python wrapper style and make it executable.

## Checks to run after the port

1. Run syntax/import checks for every new module.
2. Instantiate every backend with one supported model and confirm its model
   metadata properties.
3. Confirm an invalid model raises `UnsupportedModelError` with the supported
   names in its message.
4. Build one shared context containing user, assistant, and tool-result
   messages plus `look` and `move`.
5. For every backend, assert the exact message roles, system prompt placement,
   tool envelope, required parameter list, output-token field, headers, and
   URL.
6. Confirm `PromptBuilder.to_messages()`, `to_tools()`,
   `to_api_payload()`, `headers`, and `url` match direct backend delegation.
7. Confirm token-cost arithmetic, local Ollama's `0.0`, and Ollama Cloud's
   `None`.
8. Run `./week1_baseline/python/bin/03_prompt_builder` with the API key needed
   by the configured provider (or temporarily select local Ollama) and confirm
   it prints valid JSON without network activity.
9. Re-run `./week1_baseline/python/bin/02_the_registry` to confirm the prior
   standalone snapshot remains unaffected.

If the repository has no automated test suite for these snapshots, implement
the checks as focused `python3` smoke assertions rather than introducing a new
test framework in this step.

## Explicitly defer for later steps

- Making an HTTP request or parsing an LLM response
- Provider SDKs, retries, streaming, timeouts, and transport errors
- Tool-call request objects or executing model-selected tools
- Token counting, context-window enforcement, and truncation
- Dynamic pricing/model discovery; step 3 intentionally uses static tables
- Optional/nullable tool parameters or JSON Schema validation beyond the
  Ruby step's “all declared parameters are required” rule
- Moving tool storage from `Context` to `Registry`
- Consolidating similar provider serializers into a larger abstraction
- Any change to the task/config/registry architecture not required by Ruby
  `03_prompt_builder`
