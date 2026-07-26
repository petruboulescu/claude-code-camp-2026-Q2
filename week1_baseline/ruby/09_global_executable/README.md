# Step 9 — Install the global `boukensha` command

This step packages Boukensha as a Ruby gem. After installation, you can start
the REPL by typing `boukensha` from any directory.

You do not need to know Ruby to follow these instructions.

## 1. Build and install

Open a terminal in this folder:

```bash
cd ~/projects/claude-code-camp-2026-Q2/week1_baseline/ruby/09_global_executable
gem build boukensha.gemspec
gem install --user-install --force boukensha-0.9.0.gem
```

`--user-install` installs without `sudo`. `--force` replaces an earlier local
build of version `0.9.0`.

## 2. Make the command available

Ruby may install commands in a directory that Bash does not search. Run the
included setup helper:

```bash
ruby bin/setup-boukensha-path
source ~/.bashrc
```

If you use Zsh, the helper updates `~/.zshrc` and tells you to source that
file instead.

Verify the command:

```bash
boukensha --version
boukensha doctor
```

Expected version:

```text
boukensha 0.9.0
```

You can also open a new terminal instead of running `source ~/.bashrc`.

### Manual PATH setup

If you prefer not to run the helper, add this line to `~/.bashrc`:

```bash
export PATH="$(ruby -e 'require "rubygems"; print File.join(Gem.user_dir, "bin")'):$PATH"
```

Then reload it:

```bash
source ~/.bashrc
```

This command asks Ruby for its user executable directory, so it continues to
work when the installed Ruby version changes.

## 3. Configure Boukensha

Boukensha reads `~/.boukensharc`. Create or edit it with:

```bash
nano ~/.boukensharc
```

For this repository, use:

```yaml
boukensha_dir: ~/projects/claude-code-camp-2026-Q2/.boukensha
```

Save in Nano with Ctrl-O, Enter, then Ctrl-X.

`boukensha_dir` is where Boukensha reads:

- `.env` for API keys
- `settings.yaml` for provider and model settings
- `prompts/` for prompt overrides

The equivalent one-command override is:

```bash
BOUKENSHA_DIR=~/projects/claude-code-camp-2026-Q2/.boukensha boukensha
```

The variable is named `BOUKENSHA_DIR`.

### Optional development implementation

The installed gem contains a working copy of Boukensha. Usually you should use
that bundled copy and omit `boukensha_path`.

To make the global command load Ruby source directly from a lesson directory,
add an optional second setting:

```yaml
boukensha_dir: ~/projects/claude-code-camp-2026-Q2/.boukensha
boukensha_path: ~/projects/claude-code-camp-2026-Q2/week1_baseline/ruby/09_global_executable
```

Environment variables override both settings:

| Purpose | Environment variable | `~/.boukensharc` setting | Default |
|---|---|---|---|
| Runtime configuration | `BOUKENSHA_DIR` | `boukensha_dir` | `~/.boukensha` |
| Ruby implementation | `BOUKENSHA_PATH` | `boukensha_path` | bundled gem code |

`boukensha_path` must identify a directory containing `lib/boukensha.rb`.
It is not the shell `PATH`.

## 4. Check configuration

Run:

```bash
boukensha doctor
```

The diagnostic reports:

- Boukensha and Ruby versions
- whether Ruby's executable directory is on `PATH`
- the selected implementation and config directory
- provider and model
- whether the required credential appears to be configured

It never prints the credential value.

If `executable on PATH` says `no`, follow the command printed by `doctor`.
If `credential ready` says `no`, add the provider key to
`.boukensha/.env`, for example:

```dotenv
OPENAI_API_KEY=your-key-here
```

Supported variables are:

- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `OLLAMA_API_KEY` for Ollama Cloud

Local Ollama does not require an API key.

## 5. Run Boukensha

Start the interactive REPL:

```bash
boukensha
```

Useful commands:

```text
/help    show REPL commands
/clear   clear conversation history
/exit    leave the REPL
```

Command-line help:

```bash
boukensha --help
```

## Troubleshooting

### `boukensha: command not found`

Run:

```bash
ruby bin/setup-boukensha-path
source ~/.bashrc
hash -r
boukensha --version
```

### Changes are not visible after rebuilding

Rebuild and force-install the gem:

```bash
gem build boukensha.gemspec
gem install --user-install --force boukensha-0.9.0.gem
hash -r
```

### Inspect which command will run

```bash
command -v boukensha
boukensha doctor
```

## Why PATH is not stored in `.boukensharc`

Your shell must find the `boukensha` executable before Boukensha can read
`~/.boukensharc`. Therefore `.boukensharc` can select Boukensha configuration
and source code, but it cannot make an undiscoverable command appear on the
shell's `PATH`. The setup helper makes the required shell change instead.
