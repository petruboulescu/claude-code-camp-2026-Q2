"""Console entry point for the globally installed Boukensha command."""

from __future__ import annotations

import sys

from boukensha.version import VERSION
from boukensha_loader import LoaderError, doctor, load_and_start_repl


HELP = """Usage:
  boukensha             start the interactive REPL
  boukensha doctor      check installation and configuration
  boukensha --version   print the installed version
  boukensha --help      show this help"""


def main(argv=None, *, stdout=None, stderr=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        if not argv:
            load_and_start_repl(output=stdout)
        elif argv in (["--version"], ["-v"]):
            print(f"boukensha {VERSION}", file=stdout)
        elif argv in (["--help"], ["-h"], ["help"]):
            print(HELP, file=stdout)
        elif argv == ["doctor"]:
            doctor(output=stdout)
        else:
            print(
                f"boukensha: unknown command {' '.join(argv)!r}. "
                "Run boukensha --help.",
                file=stderr,
            )
            return 1
    except LoaderError as error:
        print(f"boukensha: {error}", file=stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
