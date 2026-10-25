"""The engine: run checks against a target, score them, and build a report.

A check is a function that receives a Context and returns (score, detail), with
score between 0 and 1. The week score is the weighted average, out of 100.
"""

import hashlib
import importlib.util
import json
import platform
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from harness import __version__
from harness.client import Exchange, Target

DATA_DIR = Path(__file__).parent / "data"

Outcome = tuple[float, str]


@dataclass(frozen=True)
class Check:
    id: str
    title: str
    weight: float
    run: Callable[["Context"], Outcome]


@dataclass
class Context:
    target: Target
    week: int
    pack: Path | None = None
    cache: dict[str, Any] = field(default_factory=dict)

    def dataset(self, name: str) -> list[dict[str, Any]]:
        """Rows from data/<name>.jsonl, or from the pack folder when it has a file with that name."""
        if name not in self.cache:
            source = (
                self.pack / f"{name}.jsonl"
                if self.pack and (self.pack / f"{name}.jsonl").exists()
                else DATA_DIR / f"{name}.jsonl"
            )
            lines = source.read_text(encoding="utf-8").splitlines()
            self.cache[name] = [json.loads(line) for line in lines if line.strip()]
        return self.cache[name]

    def once(self, key: str, compute: Callable[[], Any]) -> Any:
        """Run an expensive step (e.g. calling the endpoint for a whole dataset) only once per run."""
        if key not in self.cache:
            self.cache[key] = compute()
        return self.cache[key]


@dataclass
class CheckResult:
    id: str
    title: str
    weight: float
    score: float
    detail: str
    duration_s: float
    exchanges: list[Exchange]

    @property
    def passed(self) -> bool:
        return self.score >= 0.999

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "weight": self.weight,
            "score": round(self.score, 4),
            "passed": self.passed,
            "detail": self.detail,
            "duration_s": round(self.duration_s, 2),
            "exchanges": [e.to_dict() for e in self.exchanges],
        }


@dataclass
class Report:
    week: int
    target: str
    started_at: str
    duration_s: float
    results: list[CheckResult]
    service_info: dict[str, Any]

    @property
    def score(self) -> float:
        total = sum(r.weight for r in self.results)
        return round(100 * sum(r.weight * r.score for r in self.results) / total, 1) if total else 0.0

    def to_dict(self) -> dict[str, Any]:
        body = {
            "harness_version": __version__,
            "week": self.week,
            "target": self.target,
            "service": self.service_info,
            "started_at": self.started_at,
            "duration_s": round(self.duration_s, 1),
            "score": self.score,
            "checks": [r.to_dict() for r in self.results],
            "environment": {"python": sys.version.split()[0], "platform": platform.platform()},
        }
        canonical = json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
        body["digest"] = "sha256:" + hashlib.sha256(canonical).hexdigest()
        return body


def load_pack_checks(pack: Path | None) -> dict[int, list[Check]]:
    """A pack may add checks with a checks.py that defines EXTRA_CHECKS = {week: [Check, ...]}."""
    if not pack or not (pack / "checks.py").exists():
        return {}
    spec = importlib.util.spec_from_file_location("harness_pack_checks", pack / "checks.py")
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return dict(getattr(module, "EXTRA_CHECKS", {}))


def run_week(
    week: int, target: Target, pack: Path | None = None, progress: Callable[[str], None] | None = None
) -> Report:
    from harness.checks import CORE, WEEKS

    if week not in WEEKS:
        raise ValueError(f"No checks for week {week}. Weeks: {sorted(WEEKS)}")
    checks = [*CORE, *WEEKS[week], *load_pack_checks(pack).get(week, [])]
    ctx = Context(target=target, week=week, pack=pack)
    started, t0 = datetime.now(UTC).isoformat(timespec="seconds"), time.perf_counter()

    results: list[CheckResult] = []
    reachable = True
    for check in checks:
        if progress:
            progress(check.id)
        target.begin()
        c0 = time.perf_counter()
        if not reachable:
            score, detail = 0.0, "Skipped: the service did not answer /health."
        else:
            try:
                score, detail = check.run(ctx)
            except Exception as exc:  # noqa: BLE001 - a broken check must not stop the run
                score, detail = 0.0, f"Check crashed: {type(exc).__name__}: {exc}"
        results.append(
            CheckResult(
                check.id,
                check.title,
                check.weight,
                max(0.0, min(1.0, score)),
                detail,
                time.perf_counter() - c0,
                target.end(),
            )
        )
        if check.id == "core.health" and score == 0.0:
            reachable = False

    info = ctx.cache.get("info") or {}
    return Report(week, target.label, started, time.perf_counter() - t0, results, info)
