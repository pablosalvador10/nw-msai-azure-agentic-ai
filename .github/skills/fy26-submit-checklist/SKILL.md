---
name: fy26-submit-checklist
description: 'Pre-submission checklist for the FY26 weekly URL submission: tests and Ruff pass, the latest code is deployed (/v1/info version), student_id is set, the current week and every earlier week score on the deployed URL (the service is cumulative), Week 10 API key on and kept private, no secrets or reports committed, service left running. Use when a student asks "am I ready to submit", "what do I submit", "check my submission", "final check", or before a deadline.'
argument-hint: 'The week you are submitting (5, 6, 7, 8 or 10)'
---

# FY26 · Before you submit

You submit **one URL** per week (Week 10: the URL and your API key). Instructors run the private harness on it: the same engine as yours, with more, unseen data. Run this checklist from `fy26/` and report each item as PASS or FAIL with its evidence.

| # | Check | Command or evidence | PASS when |
|---|---|---|---|
| 1 | Offline tests | `uv run pytest -q` | No failures. Skips are fine only for features not yet due (the Week 8 spec skips until you build it) |
| 2 | Lint | `uv run ruff check .` | No errors |
| 3 | Your URL | `terraform -chdir=infra output -raw app_url` | `https://ca-....azurecontainerapps.io`, no path, no trailing slash |
| 4 | Latest code is live | `curl -s <url>/v1/info` | `version` equals the tag of your last `course.deploy()` (in `infra/image.auto.tfvars`), `student_id` is your NetID, not `anonymous`, `contract` is `fy26.v1` |
| 5 | This week scores on the URL | `uv run python -c "import course; course.setup(); course.check(<week>)"` | The score is what you expect from your in-process runs, within 1 to 2 points |
| 6 | Earlier weeks still work | the same, for each earlier week: 5, 6, 7, 8 | No earlier route broke. Your final URL is scored with every week's harness |
| 7 | Week 10 only: the key | `curl -s -o /dev/null -w "%{http_code}" -X POST <url>/v1/chat -H "content-type: application/json" -d '{"message":"hi"}'` | `401` without the key; `course.check(10)` passes `w10.auth`. Submit the key only through the course site |
| 8 | Nothing secret in git | `git status --short` and `git diff --cached --name-only` | No `.env`, `terraform.tfvars`, `*.auto.tfvars`, `terraform.tfstate*` or `reports/` staged or committed |
| 9 | It stays up | | Do not destroy the resource group or the app until grades are posted. Scale to zero keeps the cost small |

## How to report

```
Week <N> submission check
1 Tests        PASS  42 passed, 0 failed
...
URL to submit: https://ca-....azurecontainerapps.io
Scores on the URL: W5 96.2, W6 91.0
```

Do not print `SERVICE_API_KEY`, endpoint keys or subscription ids in the report.

## If something fails

| Failing item | Next step |
|---|---|
| 1, 2 | Fix locally first; a deploy will not fix a failing test |
| 4 | Deploy again (`fy26-deploy` skill) and wait until `version` changes |
| 5, 6 | Read the report (`fy26-harness` skill); fix, measure in-process, deploy |
| 7 | `course.set_api_key()`, then deploy |
| 8 | `git restore --staged <file>`; if a secret was already pushed, tell the instructors and rotate it (new key, new deploy) |

A deployed improvement counts; an undeployed one does not. If time runs short, submit the best version that is live now.
