import os
import sys
from pathlib import Path

os.environ.setdefault(
    "BOUKENSHA_DIR",
    str(Path(__file__).resolve().parents[4] / ".boukensha"),
)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import boukensha

base_dir = Path(__file__).resolve().parent.parent


def configure(dsl):
    @dsl.tool(
        "read_file",
        description="Read the contents of a file from disk",
        parameters={
            "path": {"type": "string", "description": "The file path to read"}
        },
    )
    def read_file(path):
        return (base_dir / path).read_text(encoding="utf-8")

    @dsl.tool(
        "list_directory",
        description="List the files in a directory",
        parameters={
            "path": {
                "type": "string",
                "description": "The directory path to list",
            }
        },
    )
    def list_directory(path):
        return ", ".join(
            entry.name
            for entry in (base_dir / path).iterdir()
            if not entry.name.startswith(".")
        )


print("=== BOUKENSHA Step 7: The Boukensha.run DSL ===")
print()
print(f"Config: {boukensha.config()}")
print()

result = boukensha.run(
    task=(
        "Read the README.md file and summarise what this MUD player "
        "assistant framework can do."
    ),
    configure=configure,
)

print()
print("=== FINAL RESPONSE ===")
print(result)
