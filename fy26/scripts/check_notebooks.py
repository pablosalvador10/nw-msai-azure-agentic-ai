"""Fail if a notebook is not valid JSON or still has outputs or execution counts.

Notebooks are committed clean so a diff shows only what changed in the lesson, and so
no output can leak an endpoint, a resource name or a key.

Usage: python scripts/check_notebooks.py [notebook ...]   (no arguments: every notebook here)
"""

import json
import sys
from pathlib import Path

SKIP = {".venv", ".ipynb_checkpoints"}


def problems(path: Path) -> list[str]:
    """Return what is wrong with one notebook; an empty list means it is clean."""
    try:
        notebook = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"{path}: invalid JSON ({exc})"]
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") == "code" and (cell.get("outputs") or cell.get("execution_count")):
            return [f"{path}: cell {index} has outputs; clear all outputs before committing"]
    return []


def main(argv: list[str]) -> int:
    paths = [Path(arg) for arg in argv] or sorted(Path().rglob("*.ipynb"))
    found = [issue for path in paths if not (SKIP & set(path.parts)) for issue in problems(path)]
    print("\n".join(found) or f"{len(paths)} notebooks clean")
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
