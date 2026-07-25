# The Agent Loop

The agent loop turns the one-shot API client from step 4 into a working,
bounded tool-using agent. It sends the current conversation, normalizes the
provider's response, dispatches requested tools, records their results, and
continues until the model returns a final answer.

```text
send request
     |
     v
normalize provider response
     |
     v
tool use? -- yes --> store assistant tool call
     |               dispatch every requested tool
     |               store every result
     |               repeat
     no
     |
     v
return final text
```

## What changed

| File | Change |
|---|---|
| `boukensha/agent.py` | Adds the bounded synchronous agent loop |
| `boukensha/backends/*.py` | Normalize responses and replay assistant tool calls |
| `boukensha/client.py` | Supports an explicit tools override |
| `boukensha/prompt_builder.py` | Delegates response parsing and tools overrides |
| `boukensha/tasks/base.py` | Adds iteration and output-token settings |
| `boukensha/errors.py` | Adds the reserved `LoopError` type |
| `examples/example.py` | Runs a complete live tool-use turn |

The standard-library HTTP client, retry behavior, TLS verification, model
validation, registry, context, and message types are carried forward from
step 4.

## One response shape

Each provider has a different response format. Every backend now converts its
raw response to one internal shape:

```python
{
    "stop_reason": "tool_use",  # or "end_turn"
    "content": [
        {"type": "text", "text": "I will inspect the file."},
        {
            "type": "tool_use",
            "id": "call-123",
            "name": "read_file",
            "input": {"path": "README.md"},
        },
    ],
}
```

`Agent` only handles this normalized form. It never branches on provider
names or raw response keys.

The conversion also runs in reverse. Before the next request, each backend
rebuilds its provider-specific assistant message from the stored normalized
blocks. Anthropic's content blocks already match the internal form. OpenAI
rebuilds Chat Completions `tool_calls`, Gemini rebuilds `functionCall` parts,
and the Ollama backends rebuild assistant `tool_calls`.

Anthropic and OpenAI provide unique tool-call IDs. Gemini, Ollama, and Ollama
Cloud do not provide them in these APIs, so those backends reuse the function
name as the ID and pair tool results by name.

## Agent

```python
agent = Agent(
    context=context,
    registry=registry,
    builder=builder,
    client=client,
    task_settings=player_settings,
)

result = agent.run()
```

For a tool-use response, the loop:

1. stores the complete assistant response in the context
2. dispatches every tool call synchronously and in response order
3. converts each result to text and stores it with the matching call ID
4. sends the expanded conversation back to the model

The assistant message must precede its tool results. Providers use that
ordering to match each result to the request that produced it. A model may
request multiple tools in one response; all of them run before the next model
call.

When the normalized stop reason is `end_turn`, the loop concatenates the text
blocks and returns them.

Tool callback errors, unknown tools, malformed provider responses, and
failures during normal model calls remain visible. This teaching step does not
silently recover from them.

## Turn limits and wrap-up

The player task can configure the loop:

```yaml
tasks:
  player:
    provider: anthropic
    model: claude-haiku-4-5
    prompt_override:
      system: true
    max_iterations: 25
    max_output_tokens: 1024
```

`max_iterations` defaults to `25`. A positive value is a threshold for normal
model calls; `0` or a negative value disables it. `max_output_tokens` defaults
to `1024` and is sent with every normal model call.

When the threshold is reached, the agent does not begin another work
iteration. It appends a directive asking the model to summarize its progress,
then makes exactly one extra request with:

```python
client.call(tools=[], max_output_tokens=400)
```

The empty tool list prevents another tool request during wind-down. This
terminal call is outside the counted loop. If it returns no text or raises
`ApiError`, the agent returns a deterministic message asking the user to
continue in another turn.

`LoopError` is exported for parity with the Ruby snapshot but is not raised by
this graceful threshold behavior.

## Configuration and providers

The selected task still owns its provider, model, prompt, and loop settings.
When `prompt_override.system` is true, Boukensha reads
`.boukensha/prompts/player/system.md`; otherwise it uses this snapshot's
`prompts/system.md`.

| Provider | Backend | Requirement |
|---|---|---|
| `anthropic` | `Anthropic` | `ANTHROPIC_API_KEY` |
| `openai` | `OpenAI` | `OPENAI_API_KEY` |
| `gemini` | `Gemini` | `GEMINI_API_KEY` |
| `ollama` | `Ollama` | local server at `http://localhost:11434` by default |
| `ollama_cloud` | `OllamaCloud` | `OLLAMA_API_KEY` |

The client retains step 4's four-attempt maximum, retryable HTTP statuses,
deterministic backoff, verified HTTPS, and raw JSON decoding. Backend
normalization happens only after a successful client response.

## Run the example

```sh
./week1_baseline/python/bin/05_agent_loop
```

The example asks the configured model to read this snapshot's `README.md`
through registered `read_file` and `list_directory` tools, then prints its
final summary. Relative paths are anchored at the step-5 snapshot so the
example behaves consistently from any working directory.

This is a live multi-request example. The provider must be reachable, the
configured model must support tools, and API-backed providers need valid
credentials. Calls may incur provider charges.

The path anchoring is not a security sandbox: absolute paths and `..` can
escape the snapshot directory. Production tools need an explicit permission
and containment policy; that is intentionally deferred here.
