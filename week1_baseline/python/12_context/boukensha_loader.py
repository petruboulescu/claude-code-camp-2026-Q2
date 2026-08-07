"""Resolve a Boukensha implementation and report installation health."""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Mapping, TextIO

import yaml


class LoaderError(Exception):
    """A user-facing configuration or implementation-selection error."""


def rc_file() -> Path:
    return Path.home() / ".boukensharc"


def load_rc(path: Path | None = None) -> dict[str, str]:
    path = Path(path) if path is not None else rc_file()
    if not path.exists():
        return {}

    try:
        parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise LoaderError(f"invalid YAML in {path}: {error}") from error
    except OSError as error:
        raise LoaderError(f"cannot read {path}: {error}") from error

    if parsed is None:
        return {}
    if isinstance(parsed, str):
        return {"boukensha_path": parsed}
    if not isinstance(parsed, dict):
        raise LoaderError(f"{path} must contain a YAML mapping")
    return parsed


def _expand_rc_path(value, path: Path) -> Path | None:
    if not isinstance(value, str) or not value.strip():
        return None
    expanded = Path(os.path.expanduser(value))
    return expanded.resolve() if expanded.is_absolute() else (path.parent / expanded).resolve()


def resolve(
    *,
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
) -> tuple[Path | None, Path, dict[str, str]]:
    """Return (implementation override, config directory, parsed rc)."""
    path = Path(path) if path is not None else rc_file()
    environ = os.environ if environ is None else environ
    rc = load_rc(path)

    config = environ.get("BOUKENSHA_DIR")
    config_dir = (
        Path(os.path.expanduser(config)).resolve()
        if config is not None
        else _expand_rc_path(rc.get("boukensha_dir"), path) or Path.home() / ".boukensha"
    )

    source = environ.get("BOUKENSHA_PATH")
    implementation = (
        Path(os.path.expanduser(source)).resolve()
        if source is not None
        else _expand_rc_path(rc.get("boukensha_path"), path)
    )
    if implementation is not None and not (implementation / "boukensha" / "__init__.py").is_file():
        raise LoaderError(
            "no boukensha/__init__.py found at:\n"
            f"       {implementation}\n"
            f"       Check BOUKENSHA_PATH or {path}."
        )
    return implementation, config_dir.resolve(), rc


def load_implementation(
    *,
    path: Path | None = None,
    environ: dict[str, str] | None = None,
):
    environ = os.environ if environ is None else environ
    implementation, config_dir, _ = resolve(path=path, environ=environ)
    environ.setdefault("BOUKENSHA_DIR", str(config_dir))

    if implementation is None:
        return importlib.import_module("boukensha")

    source = str(implementation)
    if source not in sys.path:
        sys.path.insert(0, source)
    for name in tuple(sys.modules):
        if name == "boukensha" or name.startswith("boukensha."):
            del sys.modules[name]
    importlib.invalidate_caches()
    return importlib.import_module("boukensha")


def load_and_start_repl(
    *,
    path: Path | None = None,
    environ: dict[str, str] | None = None,
    output: TextIO | None = None,
    argv=None,
) -> None:
    environ = os.environ if environ is None else environ
    output = sys.stdout if output is None else output
    implementation, _, _ = resolve(path=path, environ=environ)
    if environ.get("BOUKENSHA_DEBUG"):
        print(f"[boukensha] loading from: {implementation or Path(__file__).parent}", file=output)

    package = load_implementation(path=path, environ=environ)
    repl = getattr(package, "repl", None)
    if not callable(repl):
        selected = implementation or Path(package.__file__).parent.parent
        raise LoaderError(
            f"the step at {selected} does not support the interactive REPL "
            "(added in step 8); run its examples directly or select step 8 or later"
        )
    arguments = list(sys.argv[1:] if argv is None else argv)
    no_tui = "--no-tui" in arguments
    repl(tui=not no_tui)


def _read_settings(settings_file: Path) -> dict:
    if not settings_file.exists():
        return {}
    try:
        parsed = yaml.safe_load(settings_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise LoaderError(f"invalid YAML in {settings_file}: {error}") from error
    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise LoaderError(f"{settings_file} must contain a YAML mapping")
    return parsed


def _credential_present(name: str | None, env_file: Path, environ: Mapping[str, str]) -> bool:
    if name and environ.get(name, "").strip():
        return True
    if not name or not env_file.exists():
        return False
    try:
        lines = env_file.read_text(encoding="utf-8").splitlines()
    except OSError:
        return False
    for line in lines:
        key, separator, value = line.strip().partition("=")
        if separator and key == name and value.strip().strip("\"'"):
            return True
    return False


def doctor(
    *,
    path: Path | None = None,
    environ: Mapping[str, str] | None = None,
    output: TextIO | None = None,
    executable: str | None = None,
) -> None:
    from boukensha.version import VERSION

    environ = os.environ if environ is None else environ
    output = sys.stdout if output is None else output
    path = Path(path) if path is not None else rc_file()
    implementation, config_dir, _ = resolve(path=path, environ=environ)
    settings_file = config_dir / "settings.yaml"
    settings = _read_settings(settings_file)
    tasks = settings.get("tasks", {})
    player = tasks.get("player", {}) if isinstance(tasks, dict) else {}
    player = player if isinstance(player, dict) else {}
    provider = player.get("provider")
    model = player.get("model")
    credential_name = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "ollama_cloud": "OLLAMA_API_KEY",
    }.get(provider)
    credential_ready = provider == "ollama" or _credential_present(
        credential_name, config_dir / ".env", environ
    )

    executable_path = Path(executable or sys.argv[0]).resolve()
    executable_dir = executable_path.parent
    path_entries = [Path(item).resolve() for item in environ.get("PATH", "").split(os.pathsep) if item]
    on_path = executable_dir in path_entries
    bundled = Path(__file__).resolve().parent

    print("Boukensha doctor", file=output)
    print(f"  version:            {VERSION}", file=output)
    print(f"  python:             {sys.version.split()[0]}", file=output)
    print(f"  executable:         {executable_path}", file=output)
    print(f"  executable dir:     {executable_dir}", file=output)
    print(f"  executable on PATH: {'yes' if on_path else 'no'}", file=output)
    print(f"  rc file:            {path}{'' if path.exists() else ' (not found)'}", file=output)
    print(f"  implementation:     {implementation or bundled}", file=output)
    print(f"  config dir:         {config_dir}{'' if config_dir.is_dir() else ' (not found)'}", file=output)
    print(f"  settings:           {settings_file}{'' if settings_file.exists() else ' (not found)'}", file=output)
    print(f"  provider:           {provider or '(not configured)'}", file=output)
    print(f"  model:              {model or '(not configured)'}", file=output)
    print(f"  credential ready:   {'yes' if credential_ready else 'no'}", file=output)
    if not on_path:
        print(f'\nAdd the executable directory to PATH:\n  export PATH="{executable_dir}:$PATH"', file=output)
