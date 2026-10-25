"""The notebook gate used by pre-commit and CI: valid JSON, no outputs, no execution counts."""

import json
from pathlib import Path

import pytest

from scripts.check_notebooks import main, problems


def notebook(tmp_path: Path, cell: dict) -> Path:
    path = tmp_path / "lab.ipynb"
    body = {"cells": [cell], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("cell", "clean"),
    [
        ({"cell_type": "markdown", "source": "# Lab"}, True),
        ({"cell_type": "code", "source": "1 + 1", "outputs": [], "execution_count": None}, True),
        (
            {"cell_type": "code", "source": "1 + 1", "outputs": [{"output_type": "stream"}], "execution_count": None},
            False,
        ),
        ({"cell_type": "code", "source": "1 + 1", "outputs": [], "execution_count": 3}, False),
        ({"cell_type": "code", "source": "1 + 1", "outputs": [], "execution_count": 0}, False),
    ],
)
def test_only_cleared_code_cells_pass(tmp_path: Path, cell: dict, clean: bool) -> None:
    assert (problems(notebook(tmp_path, cell)) == []) is clean


def test_invalid_json_fails_the_gate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    broken = tmp_path / "broken.ipynb"
    broken.write_text("{", encoding="utf-8")

    assert main([str(broken)]) == 1
    assert "invalid JSON" in capsys.readouterr().out
