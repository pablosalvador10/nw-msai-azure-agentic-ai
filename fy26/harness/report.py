"""Write the report as JSON (the proof) and Markdown (for humans), and print a summary."""

import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from harness.engine import Report


def save(report: Report, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    base = out_dir / f"week{report.week:02d}-{stamp}-{uuid4().hex}"
    data = report.to_dict()
    json_path, md_path = base.with_suffix(".json"), base.with_suffix(".md")
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(markdown(data), encoding="utf-8")
    return json_path, md_path


def markdown(data: dict) -> str:
    service = data.get("service") or {}
    lines = [
        f"# Week {data['week']} harness report",
        "",
        f"- Target: `{data['target']}`",
        f"- Student: `{service.get('student_id', '?')}`, version `{service.get('version', '?')}`, model `{service.get('model', '?')}`",
        f"- Run: {data['started_at']} ({data['duration_s']} s), harness {data['harness_version']}",
        f"- **Score: {data['score']} / 100**",
        f"- Digest: `{data['digest']}`",
        "",
        "| Check | Weight | Score | Detail |",
        "|---|---|---|---|",
    ]
    for c in data["checks"]:
        detail = c["detail"].replace("|", "\\|")
        lines.append(f"| {c['title']} (`{c['id']}`) | {c['weight']:g} | {c['score'] * 100:.0f}% | {detail} |")
    return "\n".join(lines) + "\n"


def summary(report: Report) -> str:
    width = max(len(r.title) for r in report.results) + 2
    rows = [f"{'Check'.ljust(width)}{'Score':>7}   Detail", "-" * (width + 60)]
    for r in report.results:
        mark = "PASS" if r.passed else ("PART" if r.score > 0 else "FAIL")
        rows.append(f"{r.title.ljust(width)}{r.score * 100:>6.0f}%   [{mark}] {r.detail}")
    rows.append("-" * (width + 60))
    rows.append(f"{'Week ' + str(report.week) + ' score'.ljust(width - 5)}{report.score:>7.1f}   out of 100")
    return "\n".join(rows)
