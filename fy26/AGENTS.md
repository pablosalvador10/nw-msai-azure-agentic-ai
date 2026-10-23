# AGENTS.md · Lakeshore Ride service

Instructions for coding agents (GitHub Copilot, Claude Code, Codex and others) working in `fy26/`. People should start with [README.md](README.md).

## What this folder is

- `app/`: a FastAPI service. Routes and JSON shapes are fixed in `app/contract.py`; a harness grades them.
- `app/domain.py`: business rules (fares, stations, credits) as plain, deterministic Python. Agents call these as tools.
- `app/services/`: one module per capability (classify, ask, resolve). `app/tools.py`: tools for Agent Framework agents. `app/mcp_server.py`: the same tools over MCP.
- `harness/`: the checks and public data the service is scored on. `tests/`: offline tests.
- `infra/`: Terraform. `course.py`: notebook helpers.

## Commands (run from `fy26/`)

| Task | Command |
|---|---|
| Install | `uv sync` |
| Test (offline, seconds) | `uv run pytest` |
| Lint and format | `uv run ruff check . && uv run ruff format .` |
| Run the service | `uv run uvicorn app.main:app --reload` |
| Score without a server | `uv run python -m harness check --week <5\|6\|7\|8\|10> --in-process` |

## Rules

- Do not change `app/contract.py`, `harness/` or `harness/data/`. They define how the work is graded.
- Never let a model compute prices or make policy decisions that code can make. Put rules in `app/domain.py` and expose them as tools.
- A new tool goes in three places: the function in `app/domain.py`, an Agent Framework wrapper in `app/tools.py` if agents need it, and an MCP tool in `app/mcp_server.py` with the same name and a clear docstring.
- Tests run offline (`LLM_MODE=offline`). Never call Azure or the network from tests.
- Type hints and a one-line docstring on every public function. Ruff must pass.
- Never read, print or commit `.env`, `infra/terraform.tfvars`, `infra/*.auto.tfvars` or Terraform state.

## Done means

1. `uv run pytest` passes, and tests that were skipped because a feature was missing now run.
2. `uv run ruff check .` passes.
3. The harness score for the week you worked on did not go down.
4. You can explain the diff in three sentences.
