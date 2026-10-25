---
name: fy26-harness
description: 'Run and read the FY26 Lakeshore Ride harness: list checks, score in-process, against localhost, the deployed URL, or on the course website (Score your deployed service), find the report and proof in fy26/reports/, understand PASS/PART/FAIL, weights and noise, debug a failing check from its exchanges, pass the Week 10 API key, and improve a score without overfitting. Use when a student asks "how do I run the harness", "what does this score mean", "why did w06.ask.citations fail", "where is my report", "how am I graded", "score my URL", or "write my own check".'
argument-hint: 'Optional: the week (5, 6, 7, 8, 10) and the check id that worries you'
---

# FY26 · The harness

The harness is how the course measures your service. It sends requests to the fixed contract ([app/contract.py](../../../fy26/app/contract.py)), compares the answers with public data in [harness/data/](../../../fy26/harness/data/), and writes a report. Instructors run the same engine with more, unseen data on your URL: that is your grade.

Primer: [foundations/harness.ipynb](../../../fy26/foundations/harness.ipynb).

## Four ways to run it

All commands run from `fy26/` (the workspace root when you opened that folder in VS Code).

| Target | When | Command |
|---|---|---|
| In-process | While you iterate: no server, no deploy, uses the code in `app/` now | `uv run python -m harness check --week 6 --in-process` |
| Local server | You want to see requests in the server log, or test `/mcp` with a real client | `uv run uvicorn app.main:app --reload` in one terminal, then `uv run python -m harness check --week 6 --url http://localhost:8000` |
| Deployed URL | After `course.deploy()`: this is what gets graded | `uv run python -c "import course; course.setup(); course.check(6)"` |
| Course website | Confirm a deployment from a browser, no terminal | Sign in, open **Score your deployed service**, paste the base URL (`https://ca-...azurecontainerapps.io`, no path), pick the week |

From a notebook: `course.check(6, in_process=True)` or `course.check(6)` (your deployed URL). `course.check` runs in a fresh process, so it always sees your latest code, and it loads `fy26/.env` first.

The website runs the same public checks with the same engine. It allows one run at a time per person and 20 runs an hour, so iterate locally and use it to confirm. Its API key field (Week 10) is sent to your service for that run only and is not stored. **Download proof (JSON)** saves the same proof file the CLI writes.

`uv run python -m harness list` prints every check, its weight and its title.

In-process and local runs still call your real Foundry models with your `az login` identity, so they cost a little and take 1 to 3 minutes. Tests (`uv run pytest`) are the offline, free check.

## Week 10: the API key

Once `course.set_api_key()` has put `SERVICE_API_KEY` in `fy26/.env`, the service rejects `/v1/*` and `/mcp` without the `X-API-Key` header. The harness sends `$SERVICE_API_KEY` from the environment of its own process. `course.check(...)` loads `.env` for you. On the raw CLI, load the key into the shell first without printing it (bash or zsh: `export "$(grep '^SERVICE_API_KEY=' .env)"`; PowerShell: `$env:SERVICE_API_KEY = ((Get-Content .env | Select-String '^SERVICE_API_KEY=').Line -split '=', 2)[1]`), or pass `--api-key`. Never paste the key into a chat, an issue or a commit.

## Reading the result

```
Check                                   Score   Detail
Service is up (GET /health)              100%   [PASS] /health answered in 41 ms.
...
Week 6 score                              87.5   out of 100
```

- **Score** per check is 0 to 100%. `PART` means partial credit. The week score is the weighted average; weights are in each week's README.
- **Report:** `fy26/reports/weekNN-<time>-<id>.md`, a table for humans.
- **Proof:** the `.json` next to it. Every check lists its `exchanges`: method, path, `status`, `latency_ms`, the `request` and the `response` (bodies truncated at 2000 characters). That is where you see *what your service actually answered*.
- Exit code 2 means the first check, `core.health`, scored 0: the service is down or the URL is wrong.
- `reports/` is gitignored. You submit a URL, not these files.

## Debugging a failing check

1. Read the `Detail` column; it names what was wrong.
2. Open the newest `.json` proof and find the check by `id`. Look at three or four failing exchanges side by side.
3. Look for a **pattern**, not an item: a category the model confuses with another, a question type that never cites, a tool that is never called, a field that is missing. Patterns generalize to the hidden data; fixes for one item do not.
4. Find where that behavior is decided in `app/` (see the `fy26-labs` skill for the file of each week).
5. Change one thing. Rerun in-process. Keep the change only if the score moves beyond noise.

## Noise, and what the score predicts

Models are not deterministic. Treat a difference of one or two points as noise: run twice before you conclude. Your local score predicts the private one only if your changes generalize.

## Rules

- Never change existing checks, `harness/data/` or `app/contract.py`. They define how everyone is graded. Weakening a local check only hides a failure: the private harness uses its own copy.
- Never hardcode public items: ids, exact questions, expected answers. The private data has different items, so this scores zero there and teaches nothing.
- The service is cumulative. Before you submit, also rerun the earlier weeks against your URL: a later change can break an earlier route.

## Write your own check

A check is a function `(ctx) -> (score, detail)` registered as `Check(id, title, weight, fn)`; see [harness/checks/core.py](../../../fy26/harness/checks/core.py) for the smallest example. Week 8's lab (Part 6) walks you through writing one, and its Go further section has you add one to `harness/checks/week08.py`. Adding a new check locally is a good exercise; it does not change your grade.
