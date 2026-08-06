# Python Port Plan — 10_standard_tools

Port `week1_baseline/ruby/10_standard_tool_library` to
`week1_baseline/python/10_standard_tools` as the next standalone Python
snapshot after `week1_baseline/python/09_global_executable`.

Current starting point: the Python step-10 directory was seeded by copying the
completed Python step 9 implementation and is currently identical to it. The
copy also contains generated `build/` and `boukensha.egg-info/` directories.
This plan and the implementation are delta only.

Use an iterative migration for both the code and its guide. Keep the copied
step-9 application runnable, make one coherent MCP behavior work at a time,
document that behavior when it becomes real, and validate it before proceeding:

1. add and test a minimal generic MCP-over-stdio client
2. adapt discovered MCP tools into the existing Boukensha registry
3. parse and start configured servers, including failure and collision policy
4. integrate MCP-only tools into `run()`, `repl()`, context, and presentation
5. replace the copied step-9 guide and examples, remove generated artifacts,
   then run the full offline suite

This step turns Boukensha into an MCP host with no built-in tool library:

- spawn any stdio MCP server described by `command`, `args`, and `env`
- perform the MCP initialize handshake, discover tools, and call them
- register every discovered server tool in the normal Boukensha registry
- optionally prefix local tool names without changing names sent to the server
- reject tool-name collisions instead of silently replacing a tool
- configure all automatic tools through `mcp_servers:` in `settings.yaml`
- start required servers eagerly and fail startup when one is unavailable
- warn and continue when an optional server is unavailable
- show connected server names and discovered tool counts in the REPL banner
- retain `working_dir` only as context metadata; it grants no capability
- preserve user-defined tools added through the run DSL
- do not add built-in filesystem, shell, or MUD tools, an MCP server
  implementation, lazy server startup, non-stdio transports, or live network
  dependencies to the ordinary test suite

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/10_standard_tool_library/README.md` | MCP-host model, `mcp_servers:` format, removed tools, demos, limitations, and guide scope |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/mcp/client.rb` | JSON-RPC stdio transport, handshake, discovery, calls, and shutdown |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/tools/mcp.rb` | discovered-tool adaptation, prefixing, schema conversion, and collision errors |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/config.rb` | normalized MCP server configuration and defaults |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha.rb` | eager server registration and run/REPL integration |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/context.rb` | normalized `working_dir` metadata |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/registry.rb` | registered tool-name introspection |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/run_dsl.rb` | tool-name introspection through the DSL surface |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha/repl.rb` | server summary and step-10 diagnostics in the banner |
| `week1_baseline/ruby/10_standard_tool_library/lib/boukensha_loader.rb` | simplified global startup with no tool-specific loader arguments |
| `week1_baseline/ruby/10_standard_tool_library/bin/boukensha` | step-10 global command starts the REPL directly |
| `week1_baseline/ruby/10_standard_tool_library/boukensha.gemspec` | version `0.10.0` and absence of bundled-tool dependencies |
| `week1_baseline/ruby/10_standard_tool_library/prompts/system.md` | prompt guidance for an auto-connecting MUD MCP server |
| `week1_baseline/ruby/10_standard_tool_library/examples/` | configured full run and offline MCP/MUD smoke-demo intent |
| `week1_baseline/ruby/10_standard_tool_library/test/` | client, adapter, config, startup-policy, loader, and integration acceptance cases |

Also preserve the completed Python step 9 decisions unless this plan explicitly
changes them:

| File | Purpose |
|------|---------|
| `week1_baseline/python/09_global_executable/boukensha/run_dsl.py` | Python assembly seams, user-defined tool callback, and logger ownership |
| `week1_baseline/python/09_global_executable/boukensha/registry.py` | existing registry and dispatch behavior |
| `week1_baseline/python/09_global_executable/boukensha/tool.py` | model-facing tool representation |
| `week1_baseline/python/09_global_executable/boukensha/config.py` | safe YAML, dotenv, task settings, and installed config-directory rule |
| `week1_baseline/python/09_global_executable/boukensha/repl.py` | injectable streams and persistent interactive behavior |
| `week1_baseline/python/09_global_executable/boukensha_loader.py` | Python implementation selection and pre-import config setup |
| `week1_baseline/python/09_global_executable/pyproject.toml` | setuptools package and console-script structure |
| `week1_baseline/python/09_global_executable/tests/` | standard-library offline test style |

Treat unchanged copied files as already migrated. Do not import implementation
code from step 9. Do not retain copied `build/`, `boukensha.egg-info/`,
`__pycache__/`, `.pyc`, wheel, or source-archive artifacts.

## Behavior to preserve exactly

1. Set `VERSION = "0.10.0"` and derive distribution metadata from that
   constant so installed metadata and runtime presentation cannot drift.
2. Keep the distribution name `boukensha`, Python 3.10 minimum, the global
   `boukensha` console script, and the framework's existing `pyyaml` and
   `python-dotenv` dependencies. Add no dependency for MCP transport.
3. Boukensha ships no automatic tools of its own. An empty or absent
   `mcp_servers:` mapping leaves the agent with only tools explicitly added by
   the caller through `configure`.
4. Implement a server-agnostic MCP client under `boukensha/mcp/client.py`.
   It accepts an executable command, an argument list, and environment
   overrides; it contains no MUD, filesystem, shell, Node, or vendor logic.
5. Spawn the configured command directly as an argv sequence without a shell.
   Convert command, arguments, environment keys, and environment values to
   strings. Inherit the current process environment and let configured `env`
   keys override it.
6. Communicate over newline-delimited JSON-RPC 2.0 on the child process's
   stdin/stdout. MCP protocol messages never use the agent's user-facing
   output stream.
7. Initialize with protocol version `2025-06-18`, empty client capabilities,
   and client info containing name `boukensha` and version `0.10.0`.
8. After a successful initialize response, send
   `notifications/initialized`, then request `tools/list` eagerly. Retain the
   returned `serverInfo` and discovered tool list for diagnostics and
   registration.
9. Give each request a monotonically increasing numeric id. While waiting for
   its response, ignore blank lines, server notifications, and messages with
   other ids. A closed stdout, malformed JSON, write failure, process startup
   failure, or JSON-RPC error becomes a concise MCP client failure rather than
   a hang or unrelated traceback.
10. `call_tool(name, arguments)` sends `tools/call` with the remote name and
    arguments and returns text plus the server's `isError` state. Join all
    text content blocks in order with newlines. As in the Ruby source,
    non-text blocks are ignored and may yield an empty string.
11. Make client shutdown idempotent. Close stdin, allow the child to exit,
    terminate it when needed, reap it, and close all owned pipes. Do not leave
    MCP subprocesses or zombies after normal completion, startup failure, a
    test failure, or an exception during registration.
12. Put the registry adapter in `boukensha/tools/mcp.py`. It can spawn and
    register a configured client and can register an already-created fake
    client so adapter tests need no subprocess.
13. Map every discovered MCP tool to a normal Boukensha `Tool`: preserve its
    description, convert `inputSchema.properties` into the existing parameter
    mapping, default a missing property type to `string`, and append enum
    choices to the property description.
14. Forward tool keyword arguments with string keys and call the server using
    its original remote tool name. A tool-level `isError` is data, not a
    transport exception; return it to the agent as `error: <text>`.
15. With no prefix, expose the remote name unchanged. With a nonblank prefix,
    expose `<prefix>__<remote-name>` locally. Prefixing is client-side only.
16. Before registering each discovered name, compare it with every tool
    already present in the registry, including user-defined and earlier MCP
    tools. Raise a dedicated collision error naming the local name and
    recommending a distinct `prefix` instead of overwriting it.
17. Add `tool_names` introspection to `Registry` and `RunDSL` without changing
    ordinary registration or dispatch behavior.
18. Add `Config.mcp_servers`, returning a normalized mapping keyed by string
    server names. An absent or null block returns an empty mapping.
19. For each server entry, normalize `command` to a string, `args` to a list
    of strings, `env` to a string-to-string mapping, `prefix` to a string or
    `None`, and `required` to `True` when omitted. Match the Ruby behavior for
    malformed individual entries by treating them as empty entries, then let
    startup report the unusable command.
20. Keep the safe settings loader. Structural failures in `mcp_servers`,
    `args`, or `env` should produce a deliberate configuration/startup error,
    not execute YAML objects or fail later with an opaque Python exception.
21. At the start of both `run()` and `repl()`, create the context and registry,
    then eagerly spawn and register every configured MCP server before applying
    the caller's `configure` callback. Return a `{server_name: tool_count}`
    summary for servers that connected.
22. A configured server is required by default. If it cannot spawn,
    handshake, list tools, or register them, close its client and raise an
    error naming that server. Do not construct the backend or call the model.
23. For `required: false`, warn to stderr and continue without that server's
    tools when startup or protocol setup fails. A collision remains fatal even
    for an optional server because it is contradictory configuration, not
    server unavailability.
24. Track every successfully connected client and close all of them in reverse
    order from the outer `finally` block after `run()` or `repl()` finishes.
    Logger cleanup and MCP cleanup must both happen if the agent, REPL,
    configure callback, or later server startup raises.
25. Preserve `configure` as the existing caller-owned tool-registration escape
    hatch and apply it after automatic MCP registration, matching the Ruby
    assembly order. Do not otherwise change its decorator/direct-call API.
26. Add `working_dir` to `Context`. When supplied, store an expanded absolute
    path; when omitted directly on `Context`, store `None`.
27. Add `working_dir` to `run()` and `repl()`, defaulting to the current
    directory at call time, and pass it into `Context`. It is metadata only:
    do not change process cwd, resolve server executables, root filesystem
    access, or register a tool from it.
28. Pass the connected server summary to `Repl`. Its banner shows config
    directory status, provider/model and API-key readiness, plus either each
    `name (count)` pair or `(none configured — the agent has no tools)`.
29. Preserve REPL commands, streams, conversation history, interrupt handling,
    agent-loop behavior, backend selection, prompt construction, task limits,
    logging, and one-shot `run()` behavior from step 9.
30. Update the bundled system prompt with the Ruby step-10 MUD guidance: the
    external MUD server connects on the first gameplay action, so the agent
    should act instead of asking the user to connect it.
31. Simplify global startup to call the selected implementation's `repl()`
    without passing legacy MUD/tool arguments. The implementation still must
    be selected and `BOUKENSHA_DIR` applied before import.
32. Match the Ruby step-10 executable surface: invoking the console script
    starts the REPL directly; step-9 `doctor`, help, and version dispatch are
    no longer advertised by the step-10 guide. Do not silently retain guide
    instructions for commands the Ruby step removed.
33. Preserve rc parsing, implementation-path precedence, relative path
    resolution, development-package replacement, and useful loader errors
    still exercised by the step-10 Ruby loader tests.
34. Replace the copied README with a Python step-10 guide as the behavior is
    implemented. Explain that capabilities come from MCP config, include the
    complete server-key table, list what disappeared, and retain the Ruby
    source's current technical limitations without claiming they were fixed.
35. Provide a normal configured example and an offline protocol/adapter smoke
    example. The offline example may use a small Python fixture server or the
    repository's available MCP daemon, but it must skip cleanly when an
    external sibling fixture is absent and must not require an API key,
    network service, package installation, or user configuration.
36. Prior Python snapshots and their wrappers remain unchanged. Do not add a
    new built-in filesystem, shell, or MUD compatibility layer, and do not
    change repository-wide configuration as part of this snapshot.

## Python-specific decisions

- Use only Python's standard library for MCP transport: `subprocess`, `json`,
  and ordinary text streams. Keep `shell=False`; never compose a shell command
  string from configuration.
- Use `subprocess.Popen` with text-mode stdin/stdout/stderr and UTF-8. Keep
  protocol stdout separate from server stderr. Drain stderr safely (for
  example with a small daemon reader and bounded diagnostic tail) so a noisy
  server cannot deadlock, while never mixing stderr into JSON-RPC input.
- Define an `McpError` for transport/protocol failures and a separate
  `CollisionError` for local registry contradictions. Preserve the original
  exception as the cause when wrapping process errors.
- Validate response envelopes enough to distinguish `result` from `error` and
  include the method in failure messages. Do not implement batching,
  cancellation, progress, resources, prompts, sampling, or server-initiated
  requests in this lesson.
- Keep adapter callables bound to their own remote tool and client when
  registering inside a loop; avoid Python's late-binding closure trap.
- Do not rely only on `atexit`. The owner assembled by `run()`/`repl()` closes
  clients deterministically, while an `atexit` fallback is acceptable for
  manually registered clients.
- Use dependency injection for deterministic tests: fake `Popen` streams for
  framing/error cases, fake clients for schema/prefix/collision tests, and
  temporary executable fixture scripts for a small end-to-end stdio smoke
  test. Tests must not need Node, Ruby, `mud-manager`, an API key, or network.
- Keep `pyyaml` and `python-dotenv`; they are configuration dependencies, not
  bundled tool dependencies. Do not translate the Ruby gemspec's zero runtime
  dependencies into removing libraries the Python framework already uses.
- Include new `boukensha.mcp` and `boukensha.tools` packages explicitly in the
  setuptools package list, and keep the bundled prompt as package data.
- Update `boukensha.__init__` only for intentionally public step-10 types. The
  low-level transport can remain importable from `boukensha.mcp.client`
  without flattening every helper into the package namespace.
- Test warning output with a patched stderr stream and test REPL output with
  its existing injected stream. No test writes real settings, environment
  files, or rc files.
- The Ruby source's `bin/boukensha` ignores arguments after step 10. Implement
  the direct-start behavior deliberately and cover it; do not retain a dead
  command parser whose output contradicts the guide.

## Proposed target layout

```text
week1_baseline/python/10_standard_tools/
  pyproject.toml                  # v0.10 metadata and console entry point
  README.md                       # iterative Python MCP-host guide
  boukensha_cli.py                # direct global REPL startup
  boukensha_loader.py             # retained implementation/config selection
  boukensha/
    mcp/
      __init__.py
      client.py                   # minimal JSON-RPC stdio MCP client
    tools/
      __init__.py
      mcp.py                      # MCP discovery-to-registry adapter
    config.py                     # normalized mcp_servers settings
    context.py                    # working_dir metadata
    registry.py                   # collision-safe names/introspection
    run_dsl.py                    # eager MCP lifecycle integration
    repl.py                       # connected-server banner summary
    version.py                    # VERSION = "0.10.0"
    prompts/system.md             # step-10 external-MUD guidance
    ...                           # unchanged step-9 implementation
  examples/
    example.py                    # tools supplied entirely by settings
    mcp_demo.py                   # offline stdio discovery/call smoke demo
  tests/
    fixtures/mcp_server.py        # deterministic local stdio MCP fixture
    test_mcp_client.py            # framing, handshake, calls, errors, cleanup
    test_tools_mcp.py             # schema mapping, prefixing, dispatch, collisions
    test_mcp_servers_config.py    # normalization and required/optional policy
    ...                           # updated copied step-9 offline suite
```

## Iteration checks

After iteration 1:

- a local fixture process receives initialize, initialized, tools/list, and
  tools/call in the required order
- request ids increase and unrelated notifications/responses are ignored
- tool errors return as data and JSON-RPC/EOF/malformed-response failures are
  concise MCP errors
- configured environment overrides reach the child without losing inherited
  environment
- client close is repeatable and every test child is reaped
- the README's first runnable section explains and demonstrates the generic
  client without claiming registry integration yet

After iteration 2:

- fake discovered tools register and dispatch through the ordinary registry
- prefixed names are local while bare names go over the wire
- descriptions, property types, default string types, and enum choices reach
  the existing model-facing tool schema
- server `isError` results become `error: ...` tool output
- collisions with existing and earlier MCP tools fail with prefix guidance
- the guide documents prefixing and collision behavior with tested names

After iteration 3:

- absent `mcp_servers` yields no automatic tools
- every config field is normalized, including stringified env values and
  `required: true` by default
- multiple servers register eagerly and return accurate per-server tool counts
- required failures abort with the configured server name
- optional startup failures warn and continue, while optional collisions remain
  fatal
- partial startup failures close both the failing client and all earlier
  successfully started clients
- the guide's settings example and key/default table match the parser tests

After iteration 4:

- both `run()` and `repl()` register configured MCP tools before caller tools
  and close clients on success, interrupt, and every tested failure path
- `working_dir` is normalized context metadata and has no capability side
  effects
- the REPL banner reports server tool counts or explicitly says there are no
  configured tools
- `VERSION`, package metadata, banner, and MCP client info agree on `0.10.0`
- the global executable follows the documented direct-REPL step-10 behavior
- all copied step-9 behaviors not deliberately changed still pass
- the guide removes stale doctor/help/version and built-in-tool claims only
  after the replacement startup and diagnostics are working

After iteration 5:

- the configured example contains no built-in tool registration
- the offline demo proves spawn, handshake, discovery, prefixing, and dispatch
  without an API key or network
- README build/install/run commands use the Python step-10 directory and pip
  workflow, and accurately describe removed tools and known limitations
- focused client, adapter, config, lifecycle, loader, CLI, and REPL tests pass
- the complete standard-library offline test suite passes
- every Python file compiles
- a wheel can be built when the build frontend is available and contains both
  new subpackages, loader/CLI modules, the Boukensha package, and default prompt
- step 9 has no tracked changes
- no `build/`, `boukensha.egg-info/`, `__pycache__`, `.pyc`, wheel, source
  archive, credential, or machine-specific path is added
