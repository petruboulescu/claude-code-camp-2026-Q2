# Python Port Plan — 09_global_executable

Port `week1_baseline/ruby/09_global_executable` to
`week1_baseline/python/09_global_executable` as the next standalone Python
snapshot after `week1_baseline/python/08_the_repl_loop`.

Current starting point: the Python step-9 directory was seeded by copying the
completed Python step 8 implementation and is currently identical to it,
including copied bytecode caches. This plan and the implementation are delta
only.

Use an iterative migration. Keep the copied REPL runnable, add one coherent
behavior at a time, and validate it before proceeding:

1. add a tested loader that resolves implementation and runtime configuration
2. add the global command, help/version/doctor dispatch, and package metadata
3. align step-9 configuration and REPL presentation with the global command
4. update installation documentation and remove copied artifacts
5. run focused loader/CLI tests, then the complete offline suite

This step turns the step-8 library snapshot into an installable Python
application:

- install a global `boukensha` console command
- start the bundled step-9 REPL by default
- optionally load another Python lesson snapshot for development
- resolve command configuration from environment variables or
  `~/.boukensharc`
- provide `--help`, `--version`, and `doctor`
- report configuration readiness without printing credentials
- preserve the one-shot runner, REPL, tools, providers, and logging behavior
  from step 8
- do not add command-line task execution, arbitrary plugin imports, automatic
  shell-profile editing, live provider checks, or an installer that needs
  administrator privileges

## Source of truth (Ruby, read these to port)

| File | Purpose |
|------|---------|
| `week1_baseline/ruby/09_global_executable/README.md` | installation, rc-file, PATH, doctor, and troubleshooting workflow |
| `week1_baseline/ruby/09_global_executable/boukensha.gemspec` | package identity, version-derived build metadata, dependency, and executable declaration |
| `week1_baseline/ruby/09_global_executable/bin/boukensha` | command dispatch for REPL, doctor, version, and help |
| `week1_baseline/ruby/09_global_executable/bin/setup-boukensha-path` | intent of making a user-installed executable discoverable |
| `week1_baseline/ruby/09_global_executable/lib/boukensha_loader.rb` | rc parsing, independent setting precedence, implementation loading, diagnostics, and credential detection |
| `week1_baseline/ruby/09_global_executable/test/boukensha_loader_test.rb` | deterministic loader and doctor acceptance cases |
| `week1_baseline/ruby/09_global_executable/lib/boukensha/config.rb` | step-9 config-directory rule |
| `week1_baseline/ruby/09_global_executable/lib/boukensha/repl.rb` | simplified banner suitable for a globally installed command |
| `week1_baseline/ruby/09_global_executable/lib/boukensha/version.rb` | installed release version |

Also preserve the completed Python step 8 decisions:

| File | Purpose |
|------|---------|
| `week1_baseline/python/08_the_repl_loop/boukensha/run_dsl.py` | provider assembly and runner-owned cleanup |
| `week1_baseline/python/08_the_repl_loop/boukensha/repl.py` | persistent interactive loop and local commands |
| `week1_baseline/python/08_the_repl_loop/boukensha/config.py` | dotenv/settings loading and prompt paths |
| `week1_baseline/python/08_the_repl_loop/boukensha/version.py` | package version constant |
| `week1_baseline/python/08_the_repl_loop/tests/` | standard-library offline test style |
| `week1_baseline/python/bin/08_the_repl_loop` | repository wrapper pattern; it remains unchanged |

Treat unchanged copied files as already migrated. Do not import implementation
code from step 8 and do not retain copied `__pycache__` or `.pyc` artifacts.

## Behavior to preserve exactly

1. Package the snapshot under the distribution name `boukensha` at version
   `0.9.0`, with Python 3.10 or newer and the existing `pyyaml` and
   `python-dotenv` runtime dependencies.
2. Install a `boukensha` console script whose default action starts the
   interactive REPL.
3. Support exactly these command forms:
   `boukensha`, `boukensha doctor`, `boukensha --version`,
   `boukensha -v`, `boukensha --help`, `boukensha -h`, and
   `boukensha help`.
4. Reject unknown commands with a concise error and a pointer to
   `boukensha --help`; return a nonzero status instead of starting the REPL.
5. Keep command parsing deliberately small. Do not add `argparse` subcommand
   aliases or silently ignore extra arguments.
6. Put loader logic in `boukensha_loader.py` and command dispatch in
   `boukensha_cli.py`. The loader must be importable in offline tests without
   starting the REPL.
7. Read `~/.boukensharc` as safe YAML. Accept a mapping, an empty document,
   or the legacy single-string implementation path.
8. Reject invalid YAML and non-mapping/non-string documents with a
   user-facing loader error; never use an unsafe YAML loader.
9. Resolve `boukensha_path` and `boukensha_dir` independently. For each,
   the matching environment variable wins over the rc value.
10. Resolve relative paths from `.boukensharc` relative to the rc file's
    directory, not the caller's current working directory. Expand `~`.
11. With no implementation override, use the `boukensha` package bundled in
    the installed distribution.
12. `BOUKENSHA_PATH` or `boukensha_path` identifies a lesson directory
    containing a `boukensha/` package, not a shell executable directory.
13. Validate an overridden implementation before importing it. A missing
    `boukensha/__init__.py` produces a useful error naming the selected path.
14. Ensure the selected lesson package wins over an already importable
    bundled package for command startup. Avoid leaving a half-replaced module
    graph after validation failure.
15. Apply the resolved rc `boukensha_dir` to `BOUKENSHA_DIR` before importing
    the selected implementation, while preserving an explicit environment
    value.
16. Start the selected implementation only when it exports callable `repl`.
    If it does not, report that interactive support begins at step 8 and
    suggest running that snapshot's examples directly.
17. When `BOUKENSHA_DEBUG` is set, print the resolved implementation
    directory before starting the REPL. Otherwise startup stays quiet.
18. `--version` prints `boukensha 0.9.0` and does not construct config,
    import a development implementation, or start the REPL.
19. `doctor` reports the installed Boukensha version, Python version,
    executable location/directory, whether that directory is on `PATH`, rc
    path, selected implementation, config directory, settings file, provider,
    model, and credential readiness.
20. `doctor` tolerates a missing rc file, config directory, settings file, or
    task settings and marks missing paths rather than crashing.
21. `doctor` safely parses settings YAML. Invalid or structurally unexpected
    settings are reported as a command error rather than a traceback.
22. Determine the required credential from the configured player provider:
    `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, or
    `OLLAMA_API_KEY` for `ollama_cloud`.
23. Treat local `ollama` as credential-ready. Unknown or missing providers are
    not credential-ready.
24. Check the process environment first, then the selected config directory's
    `.env`. Recognize ordinary `KEY=value` lines without exposing the value.
25. Doctor output never contains an API-key value or the contents of `.env`.
26. If the executable directory is not on `PATH`, print a shell-neutral hint
    to add that exact directory. Do not mutate `.bashrc`, `.zshrc`, or the
    current process environment.
27. Update `Config` directory precedence for the installed step to explicit
    `BOUKENSHA_DIR`, then `~/.boukensha`. Do not inherit step 8's
    current-working-directory `.boukensha` discovery.
28. Preserve the package-level cached-config rule and all config parsing
    behavior not changed by item 27.
29. Set `VERSION = "0.9.0"` and use it for both package metadata and command
    output so the two cannot drift silently.
30. Simplify the REPL banner to show separate config, provider, and model
    lines. Do not inspect config-directory existence or display API-key
    status in the banner; `doctor` owns those diagnostics.
31. Preserve all REPL commands, persistent history, interrupt handling,
    provider assembly, logger ownership, and `run()` behavior from step 8.
32. Prior Python snapshots and the existing
    `week1_baseline/python/bin/08_the_repl_loop` wrapper remain unchanged.

## Python-specific decisions

- Use a PEP 517 `pyproject.toml` with setuptools and
  `[project.scripts] boukensha = "boukensha_cli:main"`.
- Include the `boukensha` packages and top-level loader/CLI modules in the
  wheel, plus the default `boukensha/prompts/system.md` package data.
- Keep packaging metadata declarative. Read the version dynamically from
  `boukensha.version.VERSION` rather than duplicating `0.9.0`.
- Use a small `LoaderError` exception for library-level failures. The CLI
  catches it, writes `boukensha: ...` to stderr, and returns status 1; tests
  must not need to intercept `sys.exit()` or `abort`.
- Allow loader helpers to accept explicit rc paths, environment mappings, and
  output streams where that makes deterministic tests possible. These are
  internal seams, not public `boukensha` API.
- For a development implementation, temporarily put the lesson directory at
  the front of `sys.path`, evict the existing `boukensha` package and its
  submodules, then import the selected package. The global command is a
  process boundary, so replacing that package graph is intentional.
- Keep the loader module outside the `boukensha` package so importing it for
  version/help does not eagerly import the implementation it may later
  replace.
- Use `sys.executable`, `sys.version`, `shutil.which("boukensha")`, and the
  resolved console-script path for Python diagnostics; do not translate
  RubyGems-specific paths literally.
- Python user installs normally place console scripts in the user-base
  scripts directory. Document `python -m pip install --user --force-reinstall
  .` and use `python -m site --user-base` when explaining PATH setup.
- Do not port the Ruby `setup-boukensha-path` file. Editing shell startup
  files is platform- and shell-specific; documentation and `doctor` provide
  the exact discovery guidance instead.
- Do not commit a built wheel or source archive. The checked-in Ruby `.gem`
  is a source artifact, not a requirement for the Python port.
- Test console dispatch by calling `main(argv=..., stdout=..., stderr=...)`
  directly. Add a subprocess smoke test only if it does not install anything
  or depend on the user's PATH.
- Tests use temporary homes/directories, patched environment mappings, and
  fake implementation packages. They make no network calls and do not modify
  real user configuration.

## Proposed target layout

```text
week1_baseline/python/09_global_executable/
  pyproject.toml                  # package metadata and console-script entry
  README.md                       # Python install/configure/doctor workflow
  boukensha_cli.py                # global command dispatch
  boukensha_loader.py             # rc resolution, loading, and diagnostics
  boukensha/
    version.py                    # VERSION = "0.9.0"
    config.py                     # explicit-or-home config resolution
    repl.py                       # simplified global-command banner
    ...                           # copied step-8 implementation
  boukensha/
    prompts/
      system.md                   # bundled default prompt
  tests/
    test_loader.py                # rc resolution, loading, and doctor
    test_cli.py                   # command dispatch and error statuses
    ...                           # copied step-8 offline suite
```

## Iteration checks

After iteration 1:

- mapping, legacy-string, empty, invalid, and wrong-shaped rc documents have
  deterministic results
- environment variables override rc settings independently
- relative rc paths resolve relative to the rc file
- a valid development snapshot is selected and a missing package is rejected
- `BOUKENSHA_DIR` is set before the selected implementation is imported
- the bundled package remains the default

After iteration 2:

- all documented command forms dispatch without installing the project
- default startup calls the selected snapshot's `repl()` exactly once
- help/version do not start the REPL
- unknown commands return failure and write only to stderr
- `doctor` reports useful paths and readiness without leaking a secret
- local Ollama is ready without a key; hosted providers require the matching
  environment or dotenv entry

After iteration 3:

- `VERSION`, package metadata, and `boukensha --version` agree on `0.9.0`
- step 9 ignores a current-directory `.boukensha` unless explicitly selected
- the REPL banner has separate config/provider/model lines and no credential
  status
- all copied step-8 behavioral tests still pass

After iteration 4:

- README commands use the Python step-9 directory and pip build/install flow
- `boukensha doctor` provides the PATH troubleshooting information formerly
  supplied by the Ruby helper
- no built distribution, Ruby-specific command, copied example, bytecode
  cache, or secret is part of the snapshot

After iteration 5:

- loader and CLI tests pass independently
- the complete standard-library offline test suite passes
- every Python file compiles
- a wheel can be built from the snapshot when the build frontend is available
- the built wheel contains the console entry point, loader modules, Boukensha
  package, and default prompt
- step 8 has no tracked changes
- no `__pycache__`, `.pyc`, wheel, or source archive is added
