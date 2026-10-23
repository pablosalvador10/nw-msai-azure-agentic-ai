"""Week 7: a multi-agent team resolves support cases with real actions."""

from typing import Any

from harness.checks.core import call_all
from harness.client import Exchange
from harness.engine import Check, Context, Outcome
from harness.scoring import arguments_match, fact_score, latency_score, mean


def _responses(ctx: Context) -> dict[str, Exchange]:
    rows = ctx.dataset("week07")
    return ctx.once("w07", lambda: call_all(ctx, "/v1/resolve", rows, lambda r: {"id": r["id"], "case": r["case"]}))


def _body(ex: Exchange) -> dict[str, Any]:
    body = ex.json() if ex.ok else None
    return body if isinstance(body, dict) else {}


def schema(ctx: Context) -> Outcome:
    results = _responses(ctx)
    bad = []
    for rid, ex in results.items():
        b = _body(ex)
        valid = (
            b.get("id") == rid
            and isinstance(b.get("resolution"), str)
            and b["resolution"].strip() != ""
            and isinstance(b.get("route"), list)
            and isinstance(b.get("actions"), list)
            and all(isinstance(a, dict) and {"name", "arguments", "status"} <= a.keys() for a in b["actions"])
        )
        if not valid:
            bad.append(rid)
    return 1 - len(bad) / len(results), f"{len(results) - len(bad)}/{len(results)} valid." + (
        f" Invalid: {', '.join(sorted(bad))}" if bad else ""
    )


def routing(ctx: Context) -> Outcome:
    results = _responses(ctx)
    scores, notes = [], []
    for row in ctx.dataset("week07"):
        route = set(_body(results[row["id"]]).get("route", []))
        need = set(row["specialists"])
        recall = len(route & need) / len(need)
        extra = len(route & {"policy", "billing", "operations"} - need - set(row.get("optional", [])))
        scores.append(max(0.0, recall - 0.25 * extra))
        if recall < 1 or extra:
            notes.append(f"{row['id']} (route {sorted(route)}, needs {sorted(need)})")
    return mean(scores), f"{sum(s == 1 for s in scores)}/{len(scores)} cases reached exactly the right specialists." + (
        f" {'; '.join(notes[:6])}" if notes else ""
    )


def actions(ctx: Context) -> Outcome:
    results = _responses(ctx)
    scores, notes = [], []
    for row in ctx.dataset("week07"):
        done = [a for a in _body(results[row["id"]]).get("actions", []) if isinstance(a, dict)]
        expected = row.get("actions", [])
        if not expected:
            ok = not any(a.get("name") == "issue_credit" for a in done)
            scores.append(1.0 if ok else 0.0)
            if not ok:
                notes.append(f"{row['id']} (credit issued but none was owed)")
            continue
        matched = sum(
            any(
                a.get("name") == want["name"]
                and arguments_match(a.get("arguments") or {}, want["arguments"])
                and (not want.get("status") or a.get("status") == want["status"])
                for a in done
            )
            for want in expected
        )
        spurious_credit = any(a.get("name") == "issue_credit" for a in done) and not any(
            w["name"] == "issue_credit" for w in expected
        )
        scores.append(0.0 if spurious_credit else matched / len(expected))
        if matched < len(expected):
            got = [(a.get("name"), a.get("arguments"), a.get("status")) for a in done]
            notes.append(f"{row['id']} (got {got})")
    return mean(scores), f"{sum(s == 1 for s in scores)}/{len(scores)} cases took exactly the expected actions." + (
        f" {'; '.join(notes[:6])}" if notes else ""
    )


def answer(ctx: Context) -> Outcome:
    rows = [r for r in ctx.dataset("week07") if r.get("facts")]
    results = _responses(ctx)
    scores = [fact_score(_body(results[r["id"]]).get("resolution", ""), r["facts"]) for r in rows]
    missing = [r["id"] for r, s in zip(rows, scores, strict=True) if s < 1]
    return mean(scores), f"{sum(s == 1 for s in scores)}/{len(rows)} replies state the key facts." + (
        f" Missing facts: {', '.join(missing)}" if missing else ""
    )


def latency(ctx: Context) -> Outcome:
    score, p50 = latency_score([ex.latency_ms for ex in _responses(ctx).values() if ex.ok], good_ms=20000, bad_ms=60000)
    valid, _ = schema(ctx)
    return (
        score * valid,
        f"Median /v1/resolve latency {p50 / 1000:.1f} s (full marks at 20 s or less, scaled by the share of valid responses).",
    )


CHECKS = [
    Check("w07.resolve.schema", "Every resolution matches the contract", 1.0, schema),
    Check("w07.resolve.route", "Cases reach the right specialists", 2.0, routing),
    Check("w07.resolve.actions", "Credits and tickets are correct", 3.0, actions),
    Check("w07.resolve.answer", "Replies state the key facts", 1.0, answer),
    Check("w07.latency", "Resolution latency", 1.0, latency),
]
