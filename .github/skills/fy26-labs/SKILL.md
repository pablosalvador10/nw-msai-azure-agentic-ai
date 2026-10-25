---
name: fy26-labs
description: 'Map of the FY26 Lakeshore Ride course and service, week by week: what each week builds (Week 5 classify/chat, Week 6 ask with RAG and tools, Week 7 resolve with multi-agent triage, Week 8 MCP and a coding-agent feature, Week 10 guardrails, limits and API key), the materials in each week folder (README, lecture notes and HTML, slides, required lab and its parts, optional deep dive), which file in app/ to edit, which harness checks score it, the iterate-measure-deploy loop, and common mistakes. Use when a student asks "what do I do this week", "which file do I change", "how does the app work", "where is the tool code", "what is the exercise", "where are the slides", "is the deep dive graded", or needs a hint on a lab.'
argument-hint: 'Optional: the week number (5, 6, 7, 8 or 10)'
---

# FY26 · The labs and the service, week by week

Every week has the same loop: **Learn** (concept from scratch in `lab.ipynb`) → **Build** (into `app/`) → **Test locally** (harness in-process) → **Deploy** → **Submit one URL**. The week's `README.md` is the source of truth for the exercise, the checks and the deadline; `lecture.md` holds the content.

## Calendar (Pablo-led sessions with materials)

| Week | Date | Folder | Route | Submit before |
|---|---|---|---|---|
| Setup | before Oct 27 | [setup/](../../../fy26/setup/README.md) | `/health`, `/v1/info` | Week 5 |
| 5 | Oct 27 | [week05-fundamentals-of-azure-ai](../../../fy26/week05-fundamentals-of-azure-ai/README.md) | `POST /v1/classify`, `/v1/chat` | Week 6 session |
| 6 | Nov 3 | [week06-rag-and-tool-calling](../../../fy26/week06-rag-and-tool-calling/README.md) | `POST /v1/ask` | Week 7 session |
| 7 | Nov 10 | [week07-multi-agent-systems](../../../fy26/week07-multi-agent-systems/README.md) | `POST /v1/resolve` | Week 8 session |
| 8 | Nov 17 | [week08-harnesses-and-agentic-coding](../../../fy26/week08-harnesses-and-agentic-coding/README.md) | `POST /mcp` | Week 10 session |
| 10 | Dec 1 | [week10-production-agentic-systems](../../../fy26/week10-production-agentic-systems/README.md) | all, hardened | final deadline |

Weeks 1 to 4 and 9 are taught by other instructors and have no materials here. If a tool is new, the [foundations primers](../../../fy26/foundations/README.md) take 15 to 20 minutes each.

## What each week folder holds

| File | What it is | Graded? |
|---|---|---|
| `README.md` | The exercise, files to edit, checks and weights, deadline | Defines the grade |
| `lecture.md` | The lecture notes, in numbered sections `## N · Title` | No |
| `docs/lecture.html`, `docs/slides.html` | The same notes for the browser (`lecture.html#sN` is section N) and the slide deck | No |
| `lab.ipynb` | The main lab: parts in order, then deploy. **Required** | Its result, your deployed URL, is graded |
| `deep-dive.ipynb` | Optional, for after you submit. Does not edit `app/` or deploy | No |

Open notebooks in VS Code with the kernel **`.venv (Python 3.12)`** from `fy26/.venv`. The **course website** (sign in with the GitHub account that can read the course repository) shows all of it in a browser, plus **Score your deployed service**, which runs the public harness against your URL.

## Lab parts

| Week | Parts of `lab.ipynb` |
|---|---|
| 5 | 1 Where models live · 2 First calls, from scratch · 3 Structured output · **4 Measure, then improve** (graded work) · 5 Deploy and score the live URL |
| 6 | 1 The model does not know your handbook · 2 RAG from scratch · 3 Where RAG stops · 4 Tool calling, by hand · 5 The same, with Microsoft Agent Framework · **6 Put the agent in your service** (graded work) · 7 Deploy and score · 8 Go further |
| 7 | 1 One agent with every tool · 2 Workflows, from scratch · 3 Routing with a triage agent · **4 The resolution service** (graded work) · 5 Deploy and score |
| 8 | 1 Anatomy of a harness · 2 Run the service locally · 3 Your tools, in other agents · **4 Agentic coding: a feature from a spec** (graded work) · 5 Deploy and score · 6 Write your own check |
| 10 | 1 Threat model · 2 Red-team your own service · **3 Layered guardrails** · **4 Limits and authentication** · 5 Observability · 6 Evaluation: an LLM judge from scratch · **7 Final deploy: every week, one URL** |

## Service map

| File | Role | You change it in |
|---|---|---|
| [app/contract.py](../../../fy26/app/contract.py) | Routes and JSON shapes the harness grades | **never** |
| [app/main.py](../../../fy26/app/main.py) | `create_app()`: routes, `/health`, `/ready`, `/v1/info`, mounts `/mcp` | rarely |
| [app/config.py](../../../fy26/app/config.py) | Settings from environment variables and `fy26/.env` | rarely |
| [app/models.py](../../../fy26/app/models.py) | Foundry client: Responses API, structured output (`parse`), embeddings, Agent Framework client; offline stand-ins | Week 5 (reasoning effort) |
| [app/services/classify.py](../../../fy26/app/services/classify.py), [chat.py](../../../fy26/app/services/chat.py) | `/v1/classify`, `/v1/chat` | Week 5 |
| [app/services/ask.py](../../../fy26/app/services/ask.py), [app/rag.py](../../../fy26/app/rag.py) | `/v1/ask`; chunking, embeddings, retrieval | Week 6 |
| [app/tools.py](../../../fy26/app/tools.py) | Agent tools: `search_handbook`, `quote_fare`, `get_station`, `issue_credit`, `open_ticket`; every call is recorded | Weeks 6, 7 |
| [app/domain.py](../../../fy26/app/domain.py) | Deterministic business rules: fares, stations, credits, `distance_km` | Weeks 7, 8 |
| [app/services/resolve.py](../../../fy26/app/services/resolve.py) | `/v1/resolve`: the agent team | Week 7 |
| [app/mcp_server.py](../../../fy26/app/mcp_server.py) | The same tools over MCP at `/mcp` | Week 8 |
| [app/guardrails.py](../../../fy26/app/guardrails.py), [app/middleware.py](../../../fy26/app/middleware.py) | Input screens and refusals; request ids, API key, body and rate limits | Week 10 |
| [app/data/](../../../fy26/app/data/) | The handbook pages and `stations.json`: the facts | read them |

Three rules hold every week, and [fy26/AGENTS.md](../../../fy26/AGENTS.md) states them for coding agents too:

1. The contract is fixed; how you implement it is yours.
2. Models never compute prices or make policy decisions code can make: those live in `app/domain.py` and reach the model as tools.
3. The service is cumulative: later weeks must keep earlier routes working.

## The loop, as commands

From `fy26/` (or the matching cells in `lab.ipynb`):

```bash
uv run python -m harness check --week <N> --in-process   # baseline
# change ONE thing in app/
uv run pytest                                             # offline, seconds
uv run python -m harness check --week <N> --in-process   # did it move beyond noise (1 to 2 points)?
uv run python -c "import course; course.setup(); course.deploy()"
uv run python -c "import course; course.setup(); course.check(<N>)"
```

Every lab marks a point where you stop improving and deploy. A deployed improvement counts; an undeployed one does not.

## Week by week

### Week 5 · Classify tickets

- **Edit:** `INSTRUCTIONS` in `app/services/classify.py`. The baseline only names the categories and scores in the 80s; 100 on the public data is reachable with rules (not answers) that generalize.
- **Checks:** schema, category (weight 3), urgency (2), chat, validation, median latency ≤ 4 s.
- **Think about:** what makes two categories easy to confuse; what *exactly* makes a ticket `high` urgency; whether a few contrasting examples beat more rules. The allowed values are in `Category` and `Urgency` in `app/contract.py`.
- **Common mistakes:** copying public tickets into the prompt; raising reasoning effort and blowing the latency budget; judging a prompt by one run.

### Week 6 · Answer from the handbook

- **Edit:** `app/services/ask.py`: replace retrieve-then-generate with an Agent Framework agent that uses `search_handbook`, `quote_fare` and `get_station` from `app/tools.py` and returns structured output.
- **Checks:** facts (3), citations (2, at most three `doc_id`s), tools (2: prices and station data must come from tools), abstain (1), schema, median latency ≤ 8 s.
- **Think about:** where a citation should come from (the passages the agent actually retrieved, not the model's memory); when the honest answer is "the handbook does not say"; how a tool's name and description decide whether the model calls it.
- **Common mistakes:** letting the model do fare arithmetic; citing every retrieved page; abstaining too eagerly, which costs facts points.

### Week 7 · Resolve cases with a team

- **Edit:** `app/services/resolve.py`: add a triage agent with structured output that picks only the specialists a case needs; tighten each specialist; make credits exact.
- **Checks:** route (2: right specialists and no others), actions (3: credit rider, amount and status; ticket category and station; no unowed credit), answer (1), schema, median latency ≤ 20 s.
- **Think about:** least privilege (which specialist may call `issue_credit`?); where the credit amount must come from (policy plus `domain.py`, never the model's arithmetic); what a case looks like that needs no specialist with tools.
- **Common mistakes:** running every specialist "just in case" (costs route points and latency); credits issued twice; a writer that invents actions nobody took.

### Week 8 · MCP and a feature built by a coding agent

- **Build:** `nearest_station_with_docks` in `app/domain.py`, published as an MCP tool with the same name in `app/mcp_server.py`. The spec is [tests/test_week08_nearest_station.py](../../../fy26/tests/test_week08_nearest_station.py): skipped until the function exists, then it must pass.
- **How:** a coding agent writes the code (GitHub Copilot's built-in **Agent**, picked in the Agent dropdown, reads `fy26/AGENTS.md`). You write the prompt, review every diff, run `uv run pytest tests/test_week08_nearest_station.py -q -rs` and the harness, and decide what to deploy.
- **Checks:** `w08.mcp.discover`, `w08.mcp.tools`, `w08.mcp.call` (3), `w08.mcp.new_tool` (3).
- **Try it in VS Code:** run `uv run uvicorn app.main:app --reload`, then Command Palette, **MCP: Add Server**, HTTP, `http://127.0.0.1:8000/mcp` (lab Part 3).
- **Common mistakes:** flat latitude/longitude distance instead of great-circle; returning the station itself or a full or closed one; a tool in `domain.py` but not in `mcp_server.py`.

### Week 10 · Production hardening

- **Edit:** `app/guardrails.py` (screens), `app/services/ask.py` and `resolve.py` (set `guardrail` to `"prompt_injection"` or `"unsafe"` when refusing), `app/middleware.py` if needed. Turn on the API key with `course.set_api_key()`, then deploy.
- **Checks:** injection (3), unsafe (1), limits (2), burst (2), request id, ready, auth, and regression (2: Week 6 answers still right).
- **Think about:** the false-positive cost of every screen (the regression check measures it); indirect injection inside content, not only the question; which paths must stay open (`/health`, `/ready`, `/v1/info`).
- **Finish:** run every week's harness against the final URL: `{w: course.check(w)["score"] for w in (5, 6, 7, 8, 10)}`. Submit the URL and the key through the course site, never in a public place.

## Getting help on an exercise

Ask for an explanation, a hint, or what the failing exchanges have in common. The skill `fy26-harness` explains reports; `fy26-troubleshooting` covers errors; `fy26-deploy` covers Azure.
