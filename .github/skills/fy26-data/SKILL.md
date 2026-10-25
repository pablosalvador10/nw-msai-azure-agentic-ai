---
name: fy26-data
description: 'The data behind the FY26 Lakeshore Ride course and how to analyze it: the handbook pages and how they become RAG chunks, the stations snapshot, the public harness datasets for each week and their fields, the report and proof files, tested Python recipes for patterns across failing exchanges (confusion pairs, wrong citations, latency), evaluation metrics (accuracy per class, false positives, LLM judge agreement), and Application Insights telemetry with KQL (errors, latency, tokens). Use when a student asks "what is in the handbook", "how is the data chunked", "what does the harness data contain", "what pattern do my failures share", "how many points is one miss", "which tickets get confused", "query my telemetry", or "how much does a call cost".'
argument-hint: 'Optional: the week, and the data, report or metric you want to understand'
---

# FY26 · The data, and how to read it

Every command runs from `fy26/` (the workspace root when you opened that folder in VS Code). Everything here is read-only: you analyze, you do not change the data.

## The data the service uses

| Data | Where | Shape | Used by |
|---|---|---|---|
| Handbook | [app/data/handbook/](../../../fy26/app/data/handbook/) | 10 Markdown pages. Front matter `id` (the `doc_id` you cite) and `title`; the body is split by `##` headings | `search_handbook`, `/v1/ask` citations (Week 6), policies (Week 7) |
| Stations | [app/data/stations.json](../../../fy26/app/data/stations.json) | A fixed snapshot (`snapshot` 2026-10-15) of 20 stations: `id`, `name`, `lat`, `lon`, `capacity`, `classic_available`, `ebikes_available`, `docks_available`, `status`, `seasonal`, `adaptive` | `get_station`, `list_stations`, Week 8 `nearest_station_with_docks` |
| Business rules | [app/domain.py](../../../fy26/app/domain.py) | Deterministic code: `quote_fare`, `get_station`, `distance_km`, `issue_credit` (limit `CREDIT_LIMIT` = $25), `open_ticket` | Every tool. The model never computes prices |

The snapshot is fixed so every answer is reproducible; "live" station data in this course means "read through a tool at request time", not real-time data.

## How the handbook becomes retrieval data (Week 6)

[app/rag.py](../../../fy26/app/rag.py): `load_chunks()` makes **one chunk per `##` section** of each page (text before the first `##` becomes an "Overview" chunk). `HandbookIndex` embeds every chunk with the embedding deployment (`FOUNDRY_EMBEDDING_MODEL`, `text-embedding-3-small`), and `search()` returns the `top_k=4` chunks with the highest cosine similarity. Inspect the chunks offline, without calling a model:

```bash
uv run python -c "from app.rag import load_chunks; c = load_chunks(); print(len(c), 'chunks'); [print(x.doc_id, '>', x.heading, len(x.text)) for x in c[:12]]"
```

Questions worth asking of this data: is the answer to a failing question inside one chunk, or split across two? Does a long section dilute its embedding? Does the right page rank in the top 4 for the question's wording? Lecture sections 2 to 7 and the Week 6 deep dive measure these choices.

## The public harness datasets

[harness/data/](../../../fy26/harness/data/), one JSON object per line. Public items are for understanding the *kind* of case. The private harness uses different items of the same kinds, so a rule that fits public items scores nothing there.

| File | Items | Fields |
|---|---|---|
| `week05.jsonl` | 24 tickets | `id`, `text`, expected `category` and `urgency` |
| `week06.jsonl` | 28 questions | `id`, `question`; `doc_ids` (pages a correct answer cites), `facts` (each a list of accepted spellings), `tool` (the call that must happen), `value`, `abstain` (true when the handbook does not answer) |
| `week07.jsonl` | 11 cases | `id`, `case`, `specialists` (must be called), `optional` (may be called), `actions` (expected credits and tickets with status), `facts` |
| `week08.jsonl` | 8 tool calls | `id`, `tool`, `arguments`, `expect` |
| `week10.jsonl` | 7 attacks | `id`, `question`; `canary` (an injection succeeded if it appears) or `expect: "unsafe"` |

How much one item is worth, on the public data: a week's score is the weighted average of its checks. Week 5 weights add up to 11, so one ticket with the wrong category costs 3/11 × 1/24 ≈ 1.1 points, and a wrong urgency ≈ 0.8. That is why one or two points between runs can be a single ticket, which is model noise until it repeats.

## Reports and proofs

Each harness run writes `reports/weekNN-<time>-<id>.md` (for people) and `.json` (the proof). The newest proof sorts last by name. The proof holds `score`, `service` (what `/v1/info` returned) and `checks`; each check has `id`, `weight`, `score`, `detail` and `exchanges`. An exchange is one HTTP call: `method`, `path`, `status`, `latency_ms`, `request`, `response` (bodies cut at 2,000 characters), `headers` (including `x-request-id`) and `error`.

A check's exchanges are not always stored on that check: the 24 triage calls of Week 5 appear under `w05.classify.schema`, and the accuracy checks reuse them. Collect exchanges by route and item `id` across all checks, as the recipe below does.

## Recipes (tested on real proofs)

Your service's answer to every public item, joined with what the item expects:

```python
import collections, glob, json

def latest(week):
    """The newest proof for a week, the public items, and your service's answer to each item."""
    proof = json.load(open(sorted(glob.glob(f"reports/week{week:02d}-*.json"))[-1]))
    want = {r["id"]: r for r in map(json.loads, open(f"harness/data/week{week:02d}.jsonl"))}
    got = {}
    for check in proof["checks"]:
        for ex in check["exchanges"]:
            req, res = ex.get("request"), ex.get("response")
            if isinstance(req, dict) and isinstance(res, dict) and req.get("id") in want:
                got[req["id"]] = (res, ex)
    return proof, want, got
```

Week 5, which categories get confused, and the median latency:

```python
proof, want, got = latest(5)
confusion = collections.Counter((want[i]["category"], r.get("category")) for i, (r, _) in got.items())
for (expected, predicted), n in sorted(confusion.items()):
    if expected != predicted:
        print(f"{expected:>16} -> {predicted:<16} x{n}")
latencies = sorted(ex["latency_ms"] for _, ex in got.values())
print("median latency ms", latencies[len(latencies) // 2])
```

Week 6, answers that cite none of the expected pages:

```python
proof, want, got = latest(6)
for i, (r, _) in sorted(got.items()):
    cited = {c["doc_id"] for c in r.get("citations", [])}
    expected = set(want[i].get("doc_ids", []))
    if expected and not expected & cited:
        print(f"{i}: cited {sorted(cited) or 'nothing'}, expected one of {sorted(expected)}")
```

Run them in a notebook cell after `import course; course.setup()`, or save them to a scratch file outside `app/`. Read the *pairs*, not the ids: "safety tickets go to `bike_issue`" is a pattern you can fix with a rule; "t07 is wrong" is not.

## Evaluation, as numbers

| Question | Metric | Where in the course |
|---|---|---|
| Is the triage right? | Accuracy overall and per class; the confusion pairs above | Week 5, lab Part 4 |
| Does retrieval find the page? | Share of questions whose expected `doc_id` is among the cited ones; recall@k of the retriever | Week 6, lecture section 7 |
| Does the team act correctly? | Exact match on credits and tickets; unowed actions | Week 7 |
| Do guardrails work? | Attacks caught (`w10.injection`, `w10.unsafe`) against legitimate questions refused (`w10.regression`): two error rates, tuned together | Week 10, lab Part 3 |
| Can a model grade answers? | Agreement between an LLM judge and human labels (Cohen's kappa) | Week 10, lab Part 6 |

Small datasets mean wide uncertainty: with 24 tickets, the difference between 87.5% and 91.7% category accuracy is one ticket.

## Telemetry with KQL (Week 10)

Application Insights stores your service's telemetry in Log Analytics tables: `AppRequests` (each HTTP request), `AppDependencies` (each model call, with GenAI attributes such as `gen_ai.usage.input_tokens` in `Properties`), `AppTraces` and `AppExceptions`. Traces arrive 2 to 5 minutes after the requests. From `fy26/`:

```bash
az extension add --name log-analytics --upgrade --only-show-errors   # once
WS=$(terraform -chdir=infra output -raw log_analytics_workspace_id)
az monitor log-analytics query -w $WS -o table --analytics-query "AppRequests | where TimeGenerated > ago(1h) | summarize n = count(), p50 = percentile(DurationMs, 50), p95 = percentile(DurationMs, 95), failed = countif(toint(ResultCode) >= 500) by Name"
```

Tokens per model call:

```kusto
AppDependencies
| where TimeGenerated > ago(1h) and Name startswith "chat"
| extend input_tokens = toint(Properties["gen_ai.usage.input_tokens"]),
         output_tokens = toint(Properties["gen_ai.usage.output_tokens"])
| summarize calls = count(), avg_in = avg(input_tokens), avg_out = avg(output_tokens), total = sum(input_tokens + output_tokens)
```

More queries are in the Week 10 lecture, section 12. Cost per call is (input tokens − cached) × input price + cached × cached price + output tokens × output price; the Week 5 lecture explains why reasoning tokens are already inside the output count.

## Rules

- Never look for, request or reconstruct the private grading data, and never fit rules to public items.
- Never print values from `.env`, tfvars or state; telemetry queries need only the workspace id from `terraform output`.
- Analysis is read-only. Do not edit `harness/data/`, `app/data/` or the reports.
