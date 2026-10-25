---
name: fy26-website
description: 'The FY26 course website: who can sign in (a GitHub account that can read the course repository), what it shows (course home, sessions, search, every README, lecture, slide deck, lab and deep-dive notebook as read-only pages, handbook and source files), and Score your deployed service (the public harness against your Container App URL: URL rules, the week, the Week 10 API key field, one run at a time and 20 an hour, the result, Download proof, recent runs). Use when a student asks "how do I use the course website", "I cannot sign in", "where is the score page", "the site rejects my URL", "what does the score page show", or "can I run the notebook on the website".'
argument-hint: 'Optional: what you are trying to do on the website, or the message it shows'
---

# FY26 · The course website

The course website puts the whole course in a browser behind GitHub sign-in, and adds **Score your deployed service**, the public harness run against a student's deployed URL. The instructors share its address; it is not written in the repository. It shows the same files as the repository, so anything a student reads there they can also open in VS Code.

## Signing in

- Students sign in with **GitHub**. The site admits any account that can read the course repository, and checks it at every sign-in.
- Refused? The account is not the one the instructors gave access to. Sign out of GitHub in the browser, sign in with the right account, or ask the instructors to add yours.
- A session lasts about 8 hours. **Sign out** is in the account menu.

## What it shows

| Area | What students find |
|---|---|
| Course home | The current or next session with links to its lecture, slides and main lab; every session; how each week works; setup, Foundations and the course agents |
| Sidebar and search | Every page, grouped by section. **Search** (top bar) finds lectures, labs, handbook pages and code; arrow keys move, Enter opens |
| Lectures and slides | The same `docs/lecture.html` and `docs/slides.html` as in each week folder, with a "Score your service" link |
| READMEs, lecture notes, handbook | Rendered Markdown, including Mermaid diagrams |
| Notebooks | A **read-only copy** of each lab and deep dive. Run them in VS Code, with the `.venv (Python 3.12)` kernel. **Download notebook** saves the file |
| Source files | Read-only views of `app/`, `infra/`, `harness/` and the tests. Anything the site does not show opens on GitHub (**View on GitHub**) |

## Score your deployed service

It runs the **same public checks, with the same engine**, as `uv run python -m harness check --week N --url ...`. Use it to confirm a deployment from a browser; iterate locally in between, because a local run gives the same answer without the queue.

1. Paste the **base URL** of the Container App: `https://ca-...azurecontainerapps.io`, no path, no port. Copy it from `terraform -chdir=infra output -raw app_url`.
2. Pick the week (5, 6, 7, 8 or 10).
3. Week 10, after `course.set_api_key()`: paste the value of `SERVICE_API_KEY` from `fy26/.env` into the API key field. The site sends it to the service as `X-API-Key` for that run only and does not store it.
4. **Run the harness.** A run takes one to five minutes; the first request can be slow if the app scaled to zero.

The result shows the score out of 100, every check with its detail and evidence, and what to try next. **Download proof (JSON)** saves the same proof file the CLI writes to `reports/`. **Your recent runs** lists the last ten in that browser. The service is cumulative, so score the earlier weeks on the same URL too.

Limits: one run at a time per person, and 20 runs an hour.

| Message | Meaning |
|---|---|
| "Use the https:// address of your deployed service" | The URL starts with `http://` |
| "Paste the URL of your Container App" | The address is not a `*.azurecontainerapps.io` host |
| "Paste the base URL only, without a path" | Remove `/health`, `/v1/info` or any other path |
| "Remove the user name, password or port from the URL" | Paste the plain `https://ca-...` address |
| "... does not resolve" | A typo; copy the URL from `terraform output app_url` |
| "That is the course website, not your service" | Paste your own service's URL |
| "You started 20 runs in the last hour" | Run the harness locally until the hour passes |

## What the website does not do

- It does not grade. Grades come from the instructors' private harness, with more, unseen items of the same kinds; the public score predicts it only when changes generalize.
- It does not take submissions. Submit where each week's README says.
- It does not run notebooks or deploy anything.
