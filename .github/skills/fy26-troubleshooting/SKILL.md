---
name: fy26-troubleshooting
description: 'Symptom to cause to fix table for the FY26 course: uv, kernel and ModuleNotFoundError; az login, tenant and token errors; Terraform AuthorizationFailed, InsufficientQuota, MissingSubscriptionRegistration, soft-deleted Foundry; 401/403 from Foundry; 429 or 503 model at capacity; /ready 503; harness core.health 0 or student_id anonymous; deploy timeout, failed revision, crash in the container, 500 with request_id; MCP 421 Invalid Host header; Week 10 401 Missing or invalid X-API-Key; the course website sign-in and Score your deployed service. Use for any error message, stack trace or "it does not work" in fy26.'
argument-hint: 'Paste the exact error message (remove keys and secrets first)'
---

# FY26 · Troubleshooting

Find the stage first, then the row. Work from `fy26/`. Fix the cause, then rerun only the step that failed.

## Collect evidence before guessing

| Evidence | How |
|---|---|
| Tools and sign-in | `uv run python -c "import course; course.doctor()"` |
| Which Python | `uv run python -c "import sys; print(sys.executable)"` must end in `fy26/.venv/...` |
| Service config | `GET /ready`: lists missing settings |
| What the harness saw | newest `fy26/reports/*.json`, the check's `exchanges` |
| What the container did | `az containerapp logs show -n <app> -g <rg> --type console --tail 100` (and `--type system`) |
| One failing request | its `X-Request-ID` / `request_id`, searched in the logs |

## 1 · Local environment

| Symptom | Cause | Fix |
|---|---|---|
| `uv: command not found` (or `az`, `terraform`) | Not installed, or the terminal predates the install | Install (see `fy26-setup-environment`), then open a new terminal |
| `uv sync`, `az` or `terraform init` fail with certificate, SSL or proxy errors | A network that inspects HTTPS | Try another network (a phone hotspot is enough). With uv you can also try `uv sync --native-tls` to use the system certificates |
| Kernel `.venv (Python 3.12)` not listed | VS Code has not found `fy26/.venv` | Run `uv sync` in `fy26/`; Command Palette, **Python: Select Interpreter**, choose `fy26/.venv`; reopen the notebook |
| `ModuleNotFoundError: course` or `app` in a notebook | The first cell did not run, so the notebook is not in `fy26/` | Run the notebook's first cell (`course.setup()`) |
| `ModuleNotFoundError` for a package (`agent_framework`, `fastapi`, ...) | Wrong interpreter: often the repository root `.venv`, which is FY25 and Python 3.11 | Select `fy26/.venv`, or prefix terminal commands with `uv run` from `fy26/` |
| A package you added works locally but not in Azure | Installed with `pip`, so it is not in `uv.lock`; the image uses `uv sync --frozen` | `uv add <package>` from `fy26/`, then deploy |

## 2 · Azure sign-in and Terraform

| Symptom | Cause | Fix |
|---|---|---|
| `az login` picks the wrong tenant or subscription | Several directories | `az login --tenant <tenant-id>`, then `az account set --subscription <id>` |
| `DefaultAzureCredential failed to retrieve a token`, `AADSTS...` expired or interaction required | Your `az login` session expired | `az login` again |
| `student_id must be 3-12 lowercase letters or digits` | Validation in `infra/variables.tf` | Use your NetID in lowercase, starting with a letter |
| `AuthorizationFailed` on `azurerm_resource_group` | Class subscription: you are Owner of your group only, not of the subscription | Set `RESOURCE_GROUP` to your `<netid>_resourcegroup` in setup section 3, rewrite tfvars, plan again |
| `AuthorizationFailed` on `azurerm_role_assignment` | You are Contributor only | Ask for Owner or Role Based Access Control Administrator |
| `RequestDisallowedByPolicy` | Northwestern Azure Policy allows US regions only | Use the region the setup notebook picks (`eastus2` or `eastus`) |
| `MaxNumberOfRegionalEnvironmentsInSubExceeded`, or "cannot have more than 50 environments" | The region already holds 50 Container Apps environments | Tell the instructors; do not pick another region yourself. They can move you or raise the quota |
| `InsufficientQuota` or `DeploymentModelNotSupported` | The model is not offered, or has no quota, in your region | Ask the instructors which US region to use (or lower `capacity`), then plan and apply again |
| `MissingSubscriptionRegistration` | A resource provider is not registered | `az provider register -n Microsoft.App` (or the namespace in the error), wait 2 minutes, apply again |
| Apply after a destroy: the Foundry name is taken or soft-deleted | Deleted Foundry accounts are retained | `az cognitiveservices account purge -n <name> -g <rg> -l <location>`, then apply. Only after a deliberate destroy |
| `Inconsistent dependency lock file` or provider not installed | `terraform init` never ran in this clone | `terraform -chdir=infra init` |

## 3 · Calling models (notebooks, in-process harness)

| Symptom | Cause | Fix |
|---|---|---|
| 401 or 403 from Foundry right after setup | Role assignments take minutes to propagate | Wait 2 minutes and retry; it can take up to 10 |
| 401 or 403 that does not go away | You are signed in as a different account than the one that ran `terraform apply` (only that account got **Foundry User**) | `az account show`; sign in with the account that applied, or apply again with yours |
| `KeyError: 'FOUNDRY_OPENAI_ENDPOINT'` or `/ready` 503 with a `missing` list | `fy26/.env` missing or incomplete | `uv run python -c "import course; course.write_env()"` |
| 429, or 503 "The model is at capacity" | The deployment's tokens or requests per minute are used up (100,000 tokens and 100 requests by default), often by two harness runs at once | Run one harness at a time; wait a minute. Raising `capacity` needs quota |
| The model answer is blocked with `content_filter` | Foundry's guardrails flagged the input | Expected for harmful input; the services turn it into a refusal (Week 10) |

## 4 · The harness

| Symptom | Cause | Fix |
|---|---|---|
| `core.health` 0%, exit code 2 | Service down, wrong URL, or still cold | Open `<url>/health` in a browser; check the URL starts with `https://` and has no path |
| `core.info`: `student_id is not set` | `STUDENT_ID` missing (locally in `.env`; in Azure from Terraform) | `course.write_env()` locally; redeploy for Azure |
| Score moved 1 or 2 points with no change | Model variance | Run twice before concluding |
| Score is great locally, worse on the URL | You did not deploy the change, or the old revision answered | `curl <url>/v1/info` and compare `version` with your last tag; redeploy |
| Week 10: every `/v1` call is 401 `Missing or invalid X-API-Key` | The harness process has no `SERVICE_API_KEY` | Use `course.check(...)`, which loads `.env`, or pass `--api-key` |
| `test_week08_nearest_station.py` is skipped | Expected until `app.domain.nearest_station_with_docks` exists | Implement it (Week 8); the tests then run |

## 5 · Deploy and the live service

| Symptom | Cause | Fix |
|---|---|---|
| `course.deploy()` raises `TimeoutError: ... is not serving <tag> yet` | The new revision failed to start; the old one keeps serving | `az containerapp revision list ... -o table`, then logs `--type system` and `--type console`. Usually an import error: run `uv run pytest` and the in-process harness, fix, deploy again |
| `az acr build` fails on `uv sync --frozen` | `uv.lock` out of date with `pyproject.toml` | `uv lock` (or `uv add <pkg>`), then deploy |
| Works locally, crashes in Azure on import | Code imports a file outside `app/`; only `app/`, `pyproject.toml` and `uv.lock` go into the image | Move what the service needs under `app/` (data under `app/data/`) |
| First request takes 30 to 45 s | Scale to zero while idle | Normal; the harness absorbs it |
| 500 `{"detail": "Internal error.", "request_id": ...}` | An unhandled exception in your code | Search the console logs for the `request_id`; reproduce with the in-process harness |
| `The command requires the extension log-analytics. Unable to prompt ... no tty` | `az monitor log-analytics query` is a CLI extension and a notebook cannot answer the install prompt | `az extension add --name log-analytics --upgrade` once, then rerun the cell |
| 500s in Azure right after the first deploy; console logs show 401/403 or `PermissionDenied` from Foundry | The app identity's roles are still propagating | Wait a few minutes and run the harness again (it retries 429, 502, 503 and 504, not 500) |

## 6 · MCP (Week 8)

| Symptom | Cause | Fix |
|---|---|---|
| `421 Invalid Host header` from `/mcp` | DNS-rebinding protection: only `localhost`, `127.0.0.1` and your app's own hostname (`PUBLIC_HOSTNAME`, set by Terraform) are accepted | Locally use `http://localhost:8000/mcp`, not a LAN IP; in Azure use the exact `app_url` and redeploy with Terraform if you changed it |
| `403 Invalid Origin header` | A browser-based client from another origin | Call from a non-browser client or `localhost` |
| VS Code cannot connect to the deployed `/mcp` after Week 10 | No API key header | In a **Local** chat session: add `"headers": {"X-API-Key": "${input:lakeshore-key}"}` to the server in `.vscode/mcp.json`, with a matching `inputs` entry of `"type": "promptString", "password": true`. **Copilot** sessions do not load servers that use `${input:...}`: test the deployed `/mcp` with `course.check(8)` (it sends the key), or connect VS Code to your local server, `http://127.0.0.1:8000/mcp`. Never write the key into the file |
| A new tool works in tests but not over MCP | Only added to `domain.py` | Add it to `app/mcp_server.py` with the same name and a clear docstring |

## 7 · The course website

| Symptom | Cause | Fix |
|---|---|---|
| Signed in to GitHub, but the site says the account cannot read the course | The site admits any GitHub account that can read the course repository | Sign in with the account the instructors gave access to, or ask them to add yours |
| **Score your deployed service** rejects the URL | It takes only the base URL of a Container App: `https://ca-...azurecontainerapps.io`, no path, no port | Copy it from `terraform -chdir=infra output -raw app_url` |
| "You started 20 runs in the last hour" | The site limits each person to 20 runs an hour and one at a time | Iterate with the in-process harness; use the site to confirm a deploy |
| A Week 10 run on the site: the `/v1` checks fail with 401 | The API key field was empty or wrong | Paste the value of `SERVICE_API_KEY` from `fy26/.env` into the field; the site sends it for that run only |

## Asking for help

Post: the step, the exact command, the last 20 lines of output, `course.doctor()` output, and your harness report's `Detail` lines. Remove keys, tokens and subscription ids first. Never share `.env`, `terraform.tfvars`, `secrets.auto.tfvars` or `terraform.tfstate`.
