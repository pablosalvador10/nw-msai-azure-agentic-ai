"""Keep lecture copies and policy examples aligned with the service students actually build."""

import ast
import asyncio
import re
from html.parser import HTMLParser
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.domain import CREDIT_LIMIT

COHORT = Path(__file__).resolve().parents[1]
LECTURES = sorted(COHORT.glob("week*/lecture.md"))


class LectureParts(HTMLParser):
    """Read visible headings and code without rendering or calling any model."""

    def __init__(self) -> None:
        super().__init__()
        self.collecting: str | None = None
        self.text: list[str] = []
        self.headings: list[str] = []
        self.code: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"pre", "h2"}:
            self.collecting = tag
            self.text = []

    def handle_endtag(self, tag):
        if tag == self.collecting:
            target = self.code if tag == "pre" else self.headings
            target.append("".join(self.text).strip())
            self.collecting = None

    def handle_data(self, data):
        if self.collecting:
            self.text.append(data)


def html_parts(path: Path) -> LectureParts:
    """Parse one lecture or deck from the repository."""
    parser = LectureParts()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser


@pytest.mark.parametrize("source", LECTURES, ids=lambda source: source.parent.name)
def test_lecture_numbered_sections_match_the_reading_page(source):
    expected = re.findall(r"^## (\d+) · (.+)$", source.read_text(encoding="utf-8"), re.MULTILINE)
    assert expected, f"No numbered lecture sections in {source}"
    parts = html_parts(source.parent / "docs/lecture.html")
    actual = [match.groups() for heading in parts.headings if (match := re.match(r"^(\d+)\.\s+(.+)$", heading))]
    assert actual == expected


@pytest.mark.parametrize("source", LECTURES, ids=lambda source: source.parent.name)
def test_lecture_python_examples_match_the_reading_page(source):
    expected = re.findall(r"^```python[^\n]*\n(.*?)^```", source.read_text(encoding="utf-8"), re.MULTILINE | re.DOTALL)
    parts = html_parts(source.parent / "docs/lecture.html")
    for number, block in enumerate(expected, start=1):
        assert block.strip() in parts.code, f"Python example {number} differs between {source} and its reading page"


@pytest.mark.parametrize("format", ["markdown", "lecture", "slides"])
@pytest.mark.parametrize("amount,allowed", [(CREDIT_LIMIT, True), (CREDIT_LIMIT + 0.01, False)])
def test_credit_middleware_examples_use_the_domain_policy(format, amount, allowed):
    """Execute only the illustrative gate, not the model, agent or any action tool."""
    week = COHORT / "week07-multi-agent-systems"
    if format == "markdown":
        blocks = re.findall(r"^```python[^\n]*\n(.*?)^```", (week / "lecture.md").read_text(), re.MULTILINE | re.DOTALL)
    else:
        blocks = html_parts(week / "docs" / f"{format}.html").code
    snippet = next(block for block in blocks if "async def cap_credits(" in block)
    function = next(
        node
        for node in ast.parse(snippet).body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "cap_credits"
    )
    namespace = {
        "CREDIT_LIMIT": CREDIT_LIMIT,
        "FunctionInvocationContext": SimpleNamespace,
        "function_middleware": lambda function: function,
    }
    exec(compile(ast.Module(body=[function], type_ignores=[]), "<teaching-example>", "exec"), namespace)
    context = SimpleNamespace(function=SimpleNamespace(name="issue_credit"), arguments={"amount": amount}, result=None)
    call_next = AsyncMock()
    asyncio.run(namespace["cap_credits"](context, call_next))
    assert bool(call_next.await_count) is allowed
