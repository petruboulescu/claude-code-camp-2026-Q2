from pathlib import Path

import boukensha


BASE_DIR = Path(__file__).resolve().parent.parent


def configure(dsl):
    @dsl.tool(
        "read_file",
        description="Read the contents of a UTF-8 file",
        parameters={
            "path": {
                "type": "string",
                "description": "Path relative to this step's directory",
            }
        },
    )
    def read_file(path):
        return (BASE_DIR / path).read_text(encoding="utf-8")

    @dsl.tool(
        "list_directory",
        description="List files in a directory",
        parameters={
            "path": {
                "type": "string",
                "description": "Directory relative to this step",
            }
        },
    )
    def list_directory(path):
        return ", ".join(
            sorted(
                entry.name
                for entry in (BASE_DIR / path).iterdir()
                if not entry.name.startswith(".")
            )
        )


print(f"Config: {boukensha.config()}")
boukensha.repl(configure=configure)
