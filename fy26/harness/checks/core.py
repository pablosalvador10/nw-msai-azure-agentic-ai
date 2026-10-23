"""Checks every week runs: the service is up and says who it is."""

from concurrent.futures import ThreadPoolExecutor
from typing import Any

from harness.client import Exchange
from harness.engine import Check, Context, Outcome

CONTRACT = "fy26.v1"
PARALLEL_CALLS = 4


def call_all(ctx: Context, path: str, rows: list[dict[str, Any]], body: Any) -> dict[str, Exchange]:
    """POST one request per dataset row (a few at a time). Returns {row id: exchange}."""

    def one(row: dict[str, Any]) -> tuple[str, Exchange]:
        return row["id"], ctx.target.post(path, body(row))

    with ThreadPoolExecutor(max_workers=PARALLEL_CALLS) as pool:
        return dict(pool.map(one, rows))


def health(ctx: Context) -> Outcome:
    ex = ctx.target.get("/health")
    if ex.ok and (ex.json() or {}).get("status") == "ok":
        return 1.0, f"/health answered in {ex.latency_ms:.0f} ms."
    return 0.0, f"/health returned {ex.status or ex.error}. Is the service running and the URL right?"


def info(ctx: Context) -> Outcome:
    ex = ctx.target.get("/v1/info")
    body = ex.json() if ex.ok else None
    if not isinstance(body, dict):
        return 0.0, f"/v1/info returned {ex.status or ex.error}."
    ctx.cache["info"] = body
    problems = []
    if body.get("student_id") in (None, "", "anonymous"):
        problems.append("student_id is not set (set STUDENT_ID)")
    if body.get("contract") != CONTRACT:
        problems.append(f"contract is {body.get('contract')!r}, expected {CONTRACT!r}")
    if not isinstance(body.get("capabilities"), list):
        problems.append("capabilities must be a list")
    score = 1.0 - len(problems) / 3
    return score, "; ".join(problems) or f"student_id={body['student_id']}, model={body.get('model')}."


CORE = [
    Check("core.health", "Service is up (GET /health)", 1.0, health),
    Check("core.info", "Service identifies itself (GET /v1/info)", 1.0, info),
]
