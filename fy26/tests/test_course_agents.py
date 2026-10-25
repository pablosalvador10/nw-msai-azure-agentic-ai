"""The five FY26 course agents (named after Pablo, Will and Arvind) and their skills must stay valid and agree with the course."""

import ast
import json
import re
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

COHORT = Path(__file__).resolve().parents[1]
REPO = COHORT.parent
AGENTS = sorted((REPO / ".github/agents").glob("*.agent.md"))
SKILLS = sorted((REPO / ".github/skills").glob("fy26-*/SKILL.md"))
DOCS = [*AGENTS, *SKILLS, REPO / ".github/READMEGC.md"]
# Tool aliases shared by VS Code (Local and Copilot harnesses) and GitHub Copilot custom agents.
TOOL_ALIASES = {"read", "search", "edit", "execute", "web", "todo", "agent"}
START = "Pablo · Start here"
READ_ONLY = {START, "Pablo · Fundamentals", "Pablo · Scoring", "Arvind · Data"}
MCP_FILES = [COHORT / ".mcp.json", REPO / ".mcp.json"]


def split(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path.name}: no YAML frontmatter"
    header, body = text[4:].split("\n---\n", 1)
    return yaml.safe_load(header), body


def names() -> set[str]:
    return {split(path)[0]["name"] for path in AGENTS}


def mcp_servers() -> set[str]:
    return set(json.loads((COHORT / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"])


def test_the_workspace_and_the_repository_root_both_connect_microsoft_learn() -> None:
    for path in MCP_FILES:
        server = json.loads(path.read_text(encoding="utf-8"))["mcpServers"]["microsoftLearn"]
        assert server == {"type": "http", "url": "https://learn.microsoft.com/api/mcp", "tools": ["*"]}, path


def test_five_instructor_agents_with_valid_frontmatter() -> None:
    assert [p.name for p in AGENTS] == [
        "arvind.agent.md",
        "pablo-fundamentals.agent.md",
        "pablo-scoring.agent.md",
        "pablo.agent.md",
        "will.agent.md",
    ]
    known = names()
    assert known == READ_ONLY | {"Will · Infra and deploy"}
    for path in AGENTS:
        meta, body = split(path)
        assert 40 <= len(meta["description"]) <= 1024, path.name
        assert meta.get("argument-hint"), path.name
        tools = set(meta["tools"])
        mcp = {t for t in tools if "/" in t}
        assert tools - mcp <= TOOL_ALIASES, f"{path.name}: unknown tools {tools - mcp - TOOL_ALIASES}"
        assert {t.split("/")[0] for t in mcp} <= mcp_servers(), f"{path.name}: MCP server not in .mcp.json"
        assert "microsoftLearn/*" in tools, f"{path.name} cannot reach the official docs"
        if meta["name"] in READ_ONLY:
            assert "edit" not in tools, f"{meta['name']} promises not to edit files"
        assert set(meta.get("agents", [])) <= known - {meta["name"]}, path.name
        for handoff in meta.get("handoffs", []):
            assert handoff["agent"] in known - {meta["name"]}, f"{path.name}: handoff to {handoff['agent']}"
            assert handoff["label"] and handoff["prompt"] and handoff["send"] is False
        # Students must never mistake an assistant for the instructor it is named after.
        assert f"not {meta['name'].split(' ')[0]} himself" in body, f"{path.name} must say it is an AI assistant"
        assert len(body) < 30_000, path.name


def test_the_front_door_can_consult_every_specialist() -> None:
    (meta,) = [split(path)[0] for path in AGENTS if split(path)[0]["name"] == START]
    assert set(meta["agents"]) == names() - {START}
    assert {handoff["agent"] for handoff in meta["handoffs"]} == names() - {START}


def test_skills_load_and_every_named_skill_exists() -> None:
    folders = {path.parent.name for path in SKILLS}
    assert folders == {
        "fy26-data",
        "fy26-deploy",
        "fy26-harness",
        "fy26-labs",
        "fy26-setup-environment",
        "fy26-submit-checklist",
        "fy26-troubleshooting",
        "fy26-website",
    }
    for path in SKILLS:
        meta, _ = split(path)
        # VS Code silently skips a skill whose name differs from its folder or has other characters.
        assert meta["name"] == path.parent.name and re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
        assert 40 <= len(meta["description"]) <= 1024, path.parent.name
    for path in AGENTS:
        for skill in re.findall(r"`(fy26-[a-z-]+)`", path.read_text(encoding="utf-8")):
            assert skill in folders, f"{path.name} names a missing skill {skill}"


def test_the_fy26_folder_finds_the_agents_one_level_up() -> None:
    settings = json.loads((COHORT / ".vscode/settings.json").read_text(encoding="utf-8"))
    assert settings.get("chat.useCustomizationsInParentRepositories") is True


@pytest.mark.parametrize("doc", DOCS, ids=lambda p: p.parent.name if p.name == "SKILL.md" else p.name)
def test_relative_links_resolve(doc: Path) -> None:
    for target in re.findall(r"\]\(([^)\s]+)\)", doc.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        assert (doc.parent / target.split("#")[0]).exists(), f"{doc.name}: broken link {target}"


def test_cited_course_helpers_check_ids_and_files_exist() -> None:
    from harness.checks import CORE, WEEKS

    tree = ast.parse((COHORT / "course.py").read_text(encoding="utf-8"))
    helpers = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    check_ids = {c.id for c in CORE} | {c.id for checks in WEEKS.values() for c in checks}
    cli = (COHORT / "harness/__main__.py").read_text(encoding="utf-8")
    for doc in DOCS:
        text = doc.read_text(encoding="utf-8")
        for helper in re.findall(r"\bcourse\.([a-z_]+)\(", text):
            assert helper in helpers, f"{doc.name}: course.{helper}() does not exist"
        for check in re.findall(r"`((?:core|w0[5-8]|w10)\.[a-z_.]*[a-z_])`", text):
            assert check in check_ids, f"{doc.name}: unknown check id {check}"
        for flag in re.findall(r"harness check[^`\n]*?(--[a-z-]+)", text):
            assert f'"{flag}"' in cli, f"{doc.name}: harness has no {flag} flag"
        for rel in re.findall(
            r"`((?:app|infra|harness|tests|setup|foundations)/[\w./-]+\.(?:py|tf|md|ipynb|html))`", text
        ):
            assert (COHORT / rel).exists(), f"{doc.name}: {rel} does not exist"


def test_lab_parts_in_the_week_map_match_the_notebooks() -> None:
    labs = (REPO / ".github/skills/fy26-labs/SKILL.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"^\| (5|6|7|8|10) \| (\d .+?) \|$", labs, re.MULTILINE))
    assert set(rows) == {"5", "6", "7", "8", "10"}
    for week, parts in rows.items():
        (folder,) = COHORT.glob(f"week{int(week):02d}-*")
        cells = json.loads((folder / "lab.ipynb").read_text(encoding="utf-8"))["cells"]
        headings = {line for c in cells for line in "".join(c["source"]).splitlines() if line.startswith("## Part ")}
        for part in parts.split(" \u00b7 "):
            number, title = part.replace("**", "").replace(" (graded work)", "").split(" ", 1)
            assert f"## Part {number} \u00b7 {title}" in headings, f"Week {week}: no lab part '{part}'"


def test_student_pages_name_every_agent() -> None:
    page = (COHORT / "foundations/docs/agents.html").read_text(encoding="utf-8")
    guide = (REPO / ".github/READMEGC.md").read_text(encoding="utf-8")
    for name in names():
        assert name in page and name in guide, name


def test_agents_page_teaches_calling_vibe_coding_and_every_skill() -> None:
    from harness.checks import CORE, WEEKS

    page = (COHORT / "foundations/docs/agents.html").read_text(encoding="utf-8")
    for section in ("start", "which", "agents", "call", "conversation", "vibe", "safe", "skills", "trouble"):
        assert f'<section id="{section}"' in page, section
    for path in SKILLS:
        assert f"<code>{path.parent.name}</code>" in page, f"agents.html does not list {path.parent.name}"
    check_ids = {c.id for c in CORE} | {c.id for checks in WEEKS.values() for c in checks}
    for check in re.findall(r"\b((?:core|w0[5-8]|w10)\.[a-z_]+(?:\.[a-z_]+)*)\b", page):
        assert check in check_ids, f"agents.html: unknown check id {check}"


def test_the_data_recipes_run_on_real_proofs(client, tmp_path, monkeypatch, capsys) -> None:
    """Arvind's skill gives students Python to run on their reports: it must work on a real proof."""
    from harness.client import Target
    from harness.engine import run_week
    from harness.report import save

    for week in (5, 6):
        save(run_week(week, Target(client=client)), tmp_path / "reports")
    (tmp_path / "harness").mkdir()
    (tmp_path / "harness/data").symlink_to(COHORT / "harness/data", target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    skill = (REPO / ".github/skills/fy26-data/SKILL.md").read_text(encoding="utf-8")
    blocks = re.findall(r"```python\n(.*?)```", skill, re.DOTALL)
    assert len(blocks) == 3
    namespace: dict = {}
    for block in blocks:
        exec(compile(block, "fy26-data recipe", "exec"), namespace)
    assert "median latency ms" in capsys.readouterr().out
