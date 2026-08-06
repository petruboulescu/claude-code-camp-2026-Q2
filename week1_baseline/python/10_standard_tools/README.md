# Step 10 — A Standard Tool Library

The standard tool library is **MCP**.

Boukensha ships no tools of its own. It is an MCP host: every automatic tool
the agent can call comes from an MCP server declared in `settings.yaml`. Want
file access? Plug in a filesystem server. Want to play a MUD? Plug in
`mud-manager --mcp`. With an empty `mcp_servers:` block, the agent can only
talk unless your Python caller adds a tool through `configure`.

The Ruby source directory is still named `10_standard_tool_library` from when
this lesson contained built-in filesystem, shell, and MUD tools. The Python
snapshot uses `10_standard_tools`; both names remain fixed so existing lesson
paths continue to resolve.

## Iteration 1: the generic stdio client

`boukensha.mcp.Client` starts an arbitrary command, performs the MCP initialize
handshake, discovers `tools/list`, and invokes `tools/call` over newline-delimited
JSON-RPC on stdin/stdout:

```python
from boukensha.mcp import Client

client = Client.spawn(command="mud-manager", args=["--mcp"])
try:
    print([tool["name"] for tool in client.tools])
    print(client.call_tool("look")["text"])
finally:
    client.close()
```

The client is server-agnostic. `command`, `args`, and `env` are the standard
stdio transport configuration; no MUD or filesystem behavior exists in it.
Only text MCP content blocks are joined into tool output. Images and embedded
resources are currently ignored.

## Iteration 2: registry adaptation

`boukensha.tools.mcp` adapts discovered MCP definitions to ordinary Boukensha
tools. A prefix scopes local names:

```python
from boukensha.tools.mcp import register

client = register(
    registry,
    command="mud-manager",
    args=["--mcp"],
    env={"MUD_HOST": "localhost"},
    prefix="tbamud",
)
```

The server still receives `look`; only the agent-facing name becomes
`tbamud__look`. If a local name is already registered, startup fails and asks
you to configure a distinct prefix instead of silently replacing a tool.

## Iteration 3: configure servers

Adding a capability is a settings edit, not a Boukensha code change:

```yaml
mcp_servers:
  mud:
    command: mud-manager
    args: [--mcp]
    prefix: tbamud
    env:
      MUD_HOST: your.mud.host
      MUD_NAME: Gandalf
      MUD_PASSWORD: secret

  filesystem:
    command: npx
    args: [-y, "@modelcontextprotocol/server-filesystem", /tmp]
    prefix: fs
    required: false
```

| Key | Default | Meaning |
|-----|---------|---------|
| `command` | — | Executable to spawn. The OS resolves it; a relative path depends on the current directory. |
| `args` | `[]` | Server argument vector. |
| `env` | `{}` | Extra environment. The server inherits Boukensha's environment and these keys override it. |
| `prefix` | none | Local namespace (`fs` makes `read_file` become `fs__read_file`). |
| `required` | `true` | When false, startup failure warns and the agent continues without that server. |

Servers start eagerly. Every configured process and handshake is paid at boot,
even when the model never calls its tools. A collision is always fatal,
including for an optional server, because it is contradictory configuration
rather than an unavailable capability.

## Iteration 4: run the MCP host

Create a virtual environment, install the snapshot, and run its global command:

```bash
cd week1_baseline/python/10_standard_tools
python -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install --force-reinstall .
boukensha
```

The command starts the REPL directly. Step 10 no longer advertises the step-9
`doctor`, help, or version command dispatch. Its banner reports the connected
server names and discovered tool counts, which describes what the agent can
actually do.

`working_dir` remains available on `boukensha.run()` and `boukensha.repl()` but
is context metadata only. It does not register tools, change the process
directory, or root a filesystem server. Configure a server's root in its own
arguments.

## Iteration 5: examples and tests

The normal example relies entirely on `mcp_servers:`:

```bash
BOUKENSHA_DIR=/path/to/.boukensha python examples/example.py
```

The protocol smoke demo is offline and uses the repository's tiny fixture
server—no API key, Node, live MUD, or network connection:

```bash
python examples/mcp_demo.py
```

Run the complete offline suite with:

```bash
python -m unittest discover -s tests -v
```

## What went away

| Gone | Replaced by |
|------|-------------|
| Built-in filesystem tools (`pwd`, `read_file`, `write_file`, searches, and so on) | A filesystem MCP server; its root is fixed by server arguments rather than `working_dir`. |
| Built-in `run_command` | A shell MCP server of your choosing. |
| Embedded MUD session/tools | The separate `mud-manager --mcp` server. |
| Tool-specific MUD modes and `mud:` settings | One ordinary `mcp_servers:` entry. |

`pyyaml` and `python-dotenv` remain configuration dependencies. Boukensha adds
no dependency for tools or MCP transport; servers are separate processes and
bring their own dependencies.

## Technical considerations

These are observations preserved for later lessons, not fixes in this step:

- Existing interactive MUD sessions may prompt before replacing a session;
  neither the agent nor `mud-manager` currently has a special response path.
- More purpose-built server tools may be needed to avoid inefficient sequences
  of primitive calls.
- Servers spawn eagerly, which is acceptable for a small configuration but
  should be revisited as the server count grows.
- Non-text MCP content blocks are dropped rather than rendered.
- The existing backend schema path advertises all listed parameters as
  required, even when a third-party server marks some optional.
