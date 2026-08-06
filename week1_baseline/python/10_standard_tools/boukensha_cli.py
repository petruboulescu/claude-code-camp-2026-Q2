"""Direct REPL entry point for the globally installed Boukensha command."""

from __future__ import annotations

import sys

from boukensha_loader import LoaderError, load_and_start_repl


def main(argv=None, *, stdout=None, stderr=None) -> int:
    # Step 10 deliberately has one command behavior: start the selected REPL.
    # Keep argv injectable for a small entry-point test, but do not dispatch it.
    list(sys.argv[1:] if argv is None else argv)
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    try:
        load_and_start_repl(output=stdout)
    except LoaderError as error:
        print(f"boukensha: {error}", file=stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
