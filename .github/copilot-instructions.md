# Copilot Custom Instructions

## Project Overview

This is a **teaching repository** for Northwestern University's MS AI program. Students build, deploy and harden one AI service (a support API for **Lakeshore Ride**, a fictional bike-share company) on Azure Container Apps, with Microsoft Agent Framework on Microsoft Foundry models. A local harness scores the service every week.

## Coding Standards

### Python
- Target **Python 3.12** (see `fy26/.python-version`) with type hints
- Follow **PEP 8**; Ruff is the formatter and linter (`fy26/pyproject.toml`)
- Use **docstrings** for public functions and classes; short and precise
- Prefer `pathlib.Path` over `os.path` for file operations
- Use **Pydantic** for request/response models and settings, **dataclasses** for internal data

### The service (`fy26/app/`)
- FastAPI app built by `create_app()` in `app/main.py`; settings come from environment variables via `app/config.py`
- `app/contract.py` is the fixed HTTP contract the harness grades. Changing a route or field means updating `harness/checks/`, `harness/data/`, `tests/`, and the week README in the same change
- Business rules (fares, stations) live in `app/domain.py` as plain, deterministic Python; models never compute prices
- Authenticate to Azure with managed identity / `DefaultAzureCredential` (Entra scope `https://ai.azure.com/.default`). Never add API keys for Azure services
- The MCP server (`app/mcp_server.py`) is mounted at `/mcp`; tools return JSON-serializable results and have descriptions written for agents
- The shipped week services are naive on purpose: the lab is the student's improvement. Do not replace them with the strong solution

### Infrastructure (`fy26/infra/`)
- Terraform with `azurerm ~> 5.10`; one resource group per student
- Run `terraform fmt` before committing; keep every resource readable by a beginner (one concept per file)

## Code Organization

The repo is split into self-contained **cohorts**, one folder per fiscal year. Each cohort has its own `pyproject.toml`, `.python-version`, and `.env.example`; run `uv` commands from inside the cohort folder.

```
fy26/                       # Current cohort: all new work goes here
├── README.md               # Course hub: calendar, weekly loop, grading
├── pyproject.toml          # Cohort environment (add deps with `uv add` from fy26/)
├── setup/                  # One-time setup notebook: tools, Azure, Terraform, first deploy
├── foundations/            # Start here: course-agents guide (docs/agents.html) and tool primers: Terraform, FastAPI, containers, identity, harness (docs/primers.html)
├── weekNN-<topic>/         # One folder per session: README.md, lecture.md, lab.ipynb, optional deep-dive.ipynb
│   └── docs/               # lecture.html and slides.html: lecture.md for the browser, same sections
├── assets/                 # Shared CSS/JS for the lecture pages and slide decks
├── app/                    # The FastAPI service students deploy
├── harness/                # Local harness: checks per week + public data (jsonl)
├── infra/                  # Terraform for the student's resource group
├── tests/                  # Offline pytest suite
├── course.py               # Notebook helpers; each prints the command it runs
└── Dockerfile              # Image built with `az acr build`

fy25/                       # Archived cohort: frozen, do not modify
├── src/  notebooks/  tests/  docs/
```

- Never edit an archived cohort, except to fix broken links.
- Shared assets for all cohorts (CI, Copilot skills) live in `.github/`.

## Commands (run from `fy26/`)

```bash
uv sync                                              # install
uv run ruff format . && uv run ruff check .          # format + lint
uv run pytest                                        # offline tests
uv run uvicorn app.main:app --reload                 # run the service
uv run python -m harness check --week 5 --in-process # score without deploying
```

CI (`.github/workflows/ci.yml`) runs `uv sync --locked`, Ruff, pytest, a notebook check (valid JSON, **no outputs**), and `terraform fmt -check` + `validate`.

## Security and Privacy

- Never commit `.env`, `terraform.tfvars`, `*.auto.tfvars`, `*.tfstate*`, or harness `reports/` (all gitignored)
- No real subscription IDs, tenant IDs, emails, resource names, endpoints, or keys in committed files or notebook outputs
- Hidden harness data and reference solutions stay **outside this repository**. Public data in `harness/data/` must never contain answers to hidden items
- Course content is original. Do not copy material from customer or employer repositories

## Teaching Context

- **Audience**: Graduate students in the MS AI program: smart, but often new to cloud tooling
- **Tone**: A professor's voice: concise, precise, no filler or hype
- **Explanations**: Include architecture diagrams, tables, and step-by-step reasoning
- **Examples**: Provide concrete, runnable code examples
- **Why**: Always explain *why* something works, not just *how*
- **Shape of a session**: Learn (from scratch) → Build (into `app/`) → Test locally (harness) → Deploy (Container Apps) → Submit one URL

## Testing

- Use **pytest**; shared fixtures live in `fy26/tests/conftest.py`
- Tests run **offline** (`LLM_MODE=offline`): no Azure, no network, deterministic
- Harness datasets must agree with `app/domain.py` and the handbook (`tests/test_harness_data.py`)
- A do-nothing service must score low (`tests/test_harness_end_to_end.py`); keep that true when adding checks
- Test both success and error paths

## Documentation

- Use Markdown for all documentation
- Include architecture diagrams using Mermaid
- Link to the matching Microsoft Learn module or official docs for every concept

## Dependencies

fy26 core packages (pinned in `fy26/uv.lock`):
- `fastapi`, `uvicorn` - the service
- `agent-framework-core`, `agent-framework-foundry`, `agent-framework-orchestrations` - agents and orchestration
- `openai` - Responses API client for Foundry models
- `azure-identity` - keyless authentication
- `azure-monitor-opentelemetry` - tracing to Application Insights
- `mcp` (`>=2.2,<3`, `MCPServer`) and `tenacity` - MCP server; Agent Framework's MCP client needs both
- `pytest`, `ruff`, `httpx2` - tests and tooling (`httpx2` is the HTTP client used by the test client)

## Commit Messages

Use conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `test:` - Test additions/changes
- `refactor:` - Code refactoring
