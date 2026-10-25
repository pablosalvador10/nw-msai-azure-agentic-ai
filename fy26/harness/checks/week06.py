"""Week 6: retrieval-augmented answers with citations, tool calls and abstention."""

from typing import Any

from harness.checks.core import call_all
from harness.client import Exchange
from harness.engine import Check, Context, Outcome
from harness.scoring import arguments_match, fact_score, has_number, latency_score, mean


def responses(ctx: Context, dataset: str = "week06") -> dict[str, Exchange]:
    rows = ctx.dataset(dataset)
    return ctx.once(
        f"ask:{dataset}", lambda: call_all(ctx, "/v1/ask", rows, lambda r: {"id": r["id"], "question": r["question"]})
    )


def _body(ex: Exchange) -> dict[str, Any]:
    body = ex.json() if ex.ok else None
    return body if isinstance(body, dict) else {}


def schema(ctx: Context) -> Outcome:
    results = responses(ctx)
    bad = []
    for rid, ex in results.items():
        b = _body(ex)
        valid = (
            b.get("id") == rid
            and isinstance(b.get("answer"), str)
            and isinstance(b.get("citations"), list)
            and all(isinstance(c, dict) and isinstance(c.get("doc_id"), str) for c in b["citations"])
            and isinstance(b.get("tool_calls"), list)
            and isinstance(b.get("abstained"), bool)
        )
        if not valid:
            bad.append(rid)
    return 1 - len(bad) / len(results), f"{len(results) - len(bad)}/{len(results)} valid." + (
        f" Invalid: {', '.join(sorted(bad)[:8])}" if bad else ""
    )


def facts(ctx: Context) -> Outcome:
    rows = [r for r in ctx.dataset("week06") if r.get("facts")]
    results = responses(ctx)
    scores, misses = [], []
    for row in rows:
        s = fact_score(_body(results[row["id"]]).get("answer", ""), row["facts"])
        scores.append(s)
        if s < 1:
            misses.append(row["id"])
    return mean(scores), f"{sum(s == 1 for s in scores)}/{len(rows)} answers contain every expected fact." + (
        f" Missing facts: {', '.join(misses[:8])}" if misses else ""
    )


def citations(ctx: Context) -> Outcome:
    rows = [r for r in ctx.dataset("week06") if r.get("doc_ids")]
    results = responses(ctx)
    hits, misses, crowded = [], [], []
    for row in rows:
        cited = {c.get("doc_id") for c in _body(results[row["id"]]).get("citations", []) if isinstance(c, dict)}
        hit = bool(cited & set(row["doc_ids"]))
        precise = len(cited) <= 3
        hits.append(1.0 if hit and precise else 0.5 if hit else 0.0)
        if not hit:
            misses.append(f"{row['id']} (cited {sorted(cited) or 'nothing'}, want {row['doc_ids']})")
        elif not precise:
            crowded.append(f"{row['id']} ({len(cited)} pages)")
    return mean(
        hits
    ), f"{sum(h > 0 for h in hits)}/{len(rows)} cite the right page (max 3 citations for full marks)." + (
        f" Misses: {'; '.join(misses[:5])}" if misses else ""
    ) + (f" Too many citations: {'; '.join(crowded[:5])}" if crowded else "")


def tools(ctx: Context) -> Outcome:
    rows = [r for r in ctx.dataset("week06") if r.get("tool")]
    results = responses(ctx)
    scores, notes = [], []
    for row in rows:
        b = _body(results[row["id"]])
        want = row["tool"]
        called = any(
            isinstance(c, dict)
            and c.get("name") == want["name"]
            and arguments_match(c.get("arguments") or {}, want["arguments"])
            for c in b.get("tool_calls", [])
        )
        value_ok = (
            has_number(b.get("answer", ""), row["value"])
            if "value" in row
            else fact_score(b.get("answer", ""), row.get("facts", [])) == 1
        )
        scores.append(0.5 * called + 0.5 * value_ok)
        if not (called and value_ok):
            notes.append(f"{row['id']} (tool {'ok' if called else 'missing'}, value {'ok' if value_ok else 'wrong'})")
    return mean(
        scores
    ), f"{sum(s == 1 for s in scores)}/{len(rows)} used the right tool and reported the right value." + (
        f" {'; '.join(notes[:5])}" if notes else ""
    )


def abstention(ctx: Context) -> Outcome:
    rows = ctx.dataset("week06")
    results = responses(ctx)
    wrong = [r["id"] for r in rows if _body(results[r["id"]]).get("abstained") is not bool(r.get("abstain"))]
    return 1 - len(wrong) / len(rows), (
        f"abstained is right for {len(rows) - len(wrong)}/{len(rows)} questions (true only when the handbook has no answer)."
        + (f" Wrong: {', '.join(wrong[:8])}" if wrong else "")
    )


def latency(ctx: Context) -> Outcome:
    score, p50 = latency_score([ex.latency_ms for ex in responses(ctx).values() if ex.ok], good_ms=8000, bad_ms=30000)
    valid, _ = schema(ctx)
    return (
        score * valid,
        f"Median /v1/ask latency {p50 / 1000:.1f} s (full marks at 8 s or less, scaled by the share of valid responses).",
    )


CHECKS = [
    Check("w06.ask.schema", "Every answer matches the contract", 1.0, schema),
    Check("w06.ask.facts", "Answers contain the facts from the handbook", 3.0, facts),
    Check("w06.ask.citations", "Answers cite the right handbook page", 2.0, citations),
    Check("w06.ask.tools", "Prices and stations come from tools", 2.0, tools),
    Check("w06.ask.abstain", "Says 'I don't know' only when it should", 1.0, abstention),
    Check("w06.latency", "Answer latency", 1.0, latency),
]
