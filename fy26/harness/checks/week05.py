"""Week 5: a model behind an API. Chat, ticket triage with structured output, input validation."""

from harness.checks.core import call_all
from harness.engine import Check, Context, Outcome
from harness.scoring import latency_score, mean

CATEGORIES = {"billing", "bike_issue", "station_issue", "account", "safety", "other"}
URGENCIES = {"low", "medium", "high"}


def _responses(ctx: Context) -> dict:
    rows = ctx.dataset("week05")
    return ctx.once("w05", lambda: call_all(ctx, "/v1/classify", rows, lambda r: {"id": r["id"], "text": r["text"]}))


def chat(ctx: Context) -> Outcome:
    ex = ctx.target.post("/v1/chat", {"message": "In one sentence: what can you help me with?"})
    body = ex.json() if ex.ok else None
    if not isinstance(body, dict):
        return 0.0, f"/v1/chat returned {ex.status or ex.error}."
    if not str(body.get("answer", "")).strip():
        return 0.5, "answer is empty."
    if not body.get("model"):
        return 0.75, "model is empty: report which deployment answered."
    return 1.0, f"Answered by {body['model']} in {ex.latency_ms / 1000:.1f} s."


def validation(ctx: Context) -> Outcome:
    cases = [
        ("missing field", {"id": "bad-1"}),
        ("wrong type", {"id": "bad-2", "text": 42}),
        ("empty text", {"id": "bad-3", "text": ""}),
    ]
    passed = []
    for name, body in cases:
        ex = ctx.target.post("/v1/classify", body)
        passed.append((name, ex.status is not None and 400 <= ex.status < 500))
    broken = ctx.target.request(
        "POST", "/v1/classify", content=b'{"id": "bad-4", "text": ', headers={"Content-Type": "application/json"}
    )
    passed.append(("malformed JSON", broken.status is not None and 400 <= broken.status < 500))
    failed = [name for name, ok in passed if not ok]
    return mean([1.0 if ok else 0.0 for _, ok in passed]), (
        "Rejected with 4xx: " + ", ".join(n for n, _ in passed)
    ) if not failed else f"Should be 4xx: {', '.join(failed)}"


def schema(ctx: Context) -> Outcome:
    results = _responses(ctx)
    bad = []
    for rid, ex in results.items():
        body = ex.json() if ex.ok else None
        valid = (
            isinstance(body, dict)
            and body.get("id") == rid
            and body.get("category") in CATEGORIES
            and body.get("urgency") in URGENCIES
            and isinstance(body.get("summary"), str)
            and 0 < len(body["summary"]) <= 300
        )
        if not valid:
            bad.append(rid)
    score = 1 - len(bad) / len(results)
    return score, f"{len(results) - len(bad)}/{len(results)} valid." + (
        f" Invalid: {', '.join(sorted(bad)[:8])}" if bad else ""
    )


def _accuracy(ctx: Context, field: str) -> Outcome:
    results = _responses(ctx)
    misses = []
    for row in ctx.dataset("week05"):
        body = results[row["id"]].json() or {}
        if body.get(field) != row[field]:
            misses.append(f"{row['id']} (got {body.get(field)}, want {row[field]})")
    total = len(ctx.dataset("week05"))
    return 1 - len(misses) / total, f"{total - len(misses)}/{total} correct." + (
        f" Misses: {'; '.join(misses[:6])}" if misses else ""
    )


def category(ctx: Context) -> Outcome:
    return _accuracy(ctx, "category")


def urgency(ctx: Context) -> Outcome:
    return _accuracy(ctx, "urgency")


def latency(ctx: Context) -> Outcome:
    results = _responses(ctx)
    score, p50 = latency_score([ex.latency_ms for ex in results.values() if ex.ok], good_ms=4000, bad_ms=15000)
    valid, _ = schema(ctx)
    return (
        score * valid,
        f"Median /v1/classify latency {p50 / 1000:.1f} s (full marks at 4 s or less, scaled by the share of valid responses).",
    )


CHECKS = [
    Check("w05.chat", "Chat answers (POST /v1/chat)", 1.0, chat),
    Check("w05.validation", "Bad input is rejected with 4xx", 1.0, validation),
    Check("w05.classify.schema", "Every triage response matches the contract", 1.0, schema),
    Check("w05.classify.category", "Category accuracy", 3.0, category),
    Check("w05.classify.urgency", "Urgency accuracy", 2.0, urgency),
    Check("w05.latency", "Triage latency", 1.0, latency),
]
