---
name: fy26-setup-environment
description: 'FY26 course setup for students: install uv, Azure CLI, Terraform and Git; clone the repo; uv sync; pick the fy26/.venv Jupyter kernel; az login; write terraform.tfvars; terraform init/plan/apply; write fy26/.env; first deploy and first harness score. Use when a student is new, on a new laptop, says "I am lost", "how do I set up", "kernel not found", "uv sync fails", "az login", "terraform apply", ".env missing", or asks what to do before Week 5.'
argument-hint: 'Optional: your OS (macOS, Windows, Linux) and the step you are stuck on'
---

# FY26 · Set up your environment

Source of truth: [fy26/setup/README.md](../../../fy26/setup/README.md) and [fy26/setup/setup.ipynb](../../../fy26/setup/setup.ipynb). This skill adds a state checklist and the terminal equivalent of every notebook step, so you can find exactly where a setup stopped.

## Where am I? The state checklist

Setup leaves seven artifacts behind. Check them in order; the first one missing is the next step. Every command runs from `fy26/`.

| # | Artifact | Created by | How to check |
|---|---|---|---|
| 1 | Tools: `uv`, `az`, `terraform`, `git` | You (installers below) | `uv --version`, `az version`, `terraform -version`, `git --version` |
| 2 | `fy26/.venv` (Python 3.12) | `uv sync` | `uv run python -V` prints 3.12 |
| 3 | Azure sign-in | `az login` | `az account show -o table` shows the class subscription |
| 4 | `infra/terraform.tfvars` | Notebook section 3 (`course.write_tfvars`) | The file exists (gitignored; never print or commit it) |
| 5 | Your resources | Notebook section 4 (`terraform apply`) | `terraform -chdir=infra output` lists endpoints |
| 6 | `fy26/.env` | Notebook section 5 (`course.write_env()`) | The file exists and has `STUDENT_ID`, `FOUNDRY_*`, `APP_URL` keys |
| 7 | A running service | Notebook section 7 (`course.deploy()`) | `terraform -chdir=infra output app_url` is not empty and `<url>/health` answers `{"status":"ok"}` |

One command checks 1 to 3 for you:

```bash
uv run python -c "import course; course.doctor()"
```

When you report the state of `.env` or `terraform.tfvars`, name the keys that are present. Never print their values.

## 1. Install the tools

| Tool | macOS | Windows (PowerShell) | Official page |
|---|---|---|---|
| uv | `brew install uv` or `curl -LsSf https://astral.sh/uv/install.sh \| sh` | `winget install --id=astral-sh.uv -e` | [Install uv](https://docs.astral.sh/uv/getting-started/installation/) |
| Azure CLI | `brew install azure-cli` | `winget install -e --id Microsoft.AzureCLI` | [Install the Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| Terraform | `brew tap hashicorp/tap && brew install hashicorp/tap/terraform` | `winget install Hashicorp.Terraform` | [Install Terraform](https://developer.hashicorp.com/terraform/install) |
| Git | `xcode-select --install` or `brew install git` | `winget install --id Git.Git -e` | [git-scm.com](https://git-scm.com/downloads) |
| VS Code + Python + Jupyter extensions | | | [code.visualstudio.com](https://code.visualstudio.com/) |

On Linux, follow the official pages. After installing, **open a new terminal** so the new commands are on your `PATH`. You do not need Docker: images are built in Azure.

## 2. Get the course and its environment

```bash
git clone https://github.com/pablosalvador10/northwestern-msai-azure-agentic-ai.git
cd northwestern-msai-azure-agentic-ai/fy26
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, downloads Python 3.12 if needed, and creates `fy26/.venv` with the exact versions everyone uses. Why a lockfile: the whole class, the tests and your container run the same packages, so "works on my machine" means it works everywhere.

Open the `fy26` folder in VS Code. In a notebook, choose the kernel **`.venv (Python 3.12)`** from `fy26/.venv`. If it is not listed: Command Palette, **Python: Select Interpreter**, pick `fy26/.venv`, reopen the notebook.

> The repository root may also contain a `.venv`: that one belongs to the archived FY25 course (Python 3.11). Always use `fy26/.venv`.

## 3. Azure access

- **Northwestern class subscription:** a resource group named like `<netid>_resourcegroup` already exists for you, and you are **Owner of that group only**. You cannot create resource groups, so set `RESOURCE_GROUP` in the notebook's section 3 to that name. Azure Policy allows **US regions only**, and a region holds at most 50 Container Apps environments, so the notebook splits the class by the last digit of the NetID: 0 to 4 use `eastus2`, 5 to 9 use `eastus`. Do not change it unless the instructors say so.
- **Your own subscription:** you need **Owner**, or **Contributor** plus **Role Based Access Control Administrator**. Leave `RESOURCE_GROUP` empty and Terraform creates `rg-nu-<student_id>`. Contributor alone cannot assign roles.
- The region must offer the models in [infra/variables.tf](../../../fy26/infra/variables.tf), with quota. Ask before changing it.
- Several tenants? `az login --tenant <tenant-id>`, then `az account set --subscription <id>`.

## 4. The notebook steps and their terminal equivalents

[setup.ipynb](../../../fy26/setup/setup.ipynb) runs these for you; each helper in [course.py](../../../fy26/course.py) prints the command it runs. Use the terminal versions to redo one step.

| Notebook section | What it does | Terminal (from `fy26/`) |
|---|---|---|
| 1 · Check your tools | Versions and sign-in | `uv run python -c "import course; course.doctor()"` |
| 2 · Sign in to Azure | Browser sign-in | `az login` |
| 3 · Tell Terraform who you are | Writes `infra/terraform.tfvars` | `uv run python -c "import course; course.write_tfvars('<netid>', '<eastus2 or eastus>', resource_group='<netid>_resourcegroup', create_resource_group=False)"` (own subscription: drop the last two arguments) |
| 4 · Create your resources | Foundry, models, registry, Container Apps environment, monitoring, identity (about 5 min). The plan shows 12 to add (13 if Terraform creates the group) | `terraform -chdir=infra init` then `terraform -chdir=infra plan -out=tfplan` then `terraform -chdir=infra apply tfplan` |
| 5 · Connect the notebooks | Writes `fy26/.env` from Terraform outputs | `uv run python -c "import course; course.write_env()"` |
| 6 · Call a model, no key | Proves your identity can call Foundry | Run the cell; a 401/403 in the first minutes is role propagation |
| 7 · Build and deploy | `az acr build`, then `terraform apply` with the new image tag (4 to 6 min) | `uv run python -c "import course; course.setup(); course.deploy()"` |
| 8 · Score it | Runs the Week 5 harness against your URL | `uv run python -c "import course; course.setup(); course.check(5)"` |

`student_id` must be 3 to 12 lowercase letters or digits and start with a letter (your NetID works). It names your resources and is what `/v1/info` returns to the harness.

## 5. Done means

- `course.doctor()` shows every tool and your Azure account.
- `terraform -chdir=infra output app_url` prints an `https://ca-...azurecontainerapps.io` URL.
- The Week 5 harness runs against that URL and `core.health` and `core.info` pass. A score in the 80s is normal before the Week 5 lab.

## If a step fails

Look up the exact error in the `fy26-troubleshooting` skill or the table in [setup/README.md](../../../fy26/setup/README.md#if-something-goes-wrong). Fix the cause, then rerun only the failed step: Terraform and the helpers are idempotent, so rerunning is safe.

Never run `terraform -chdir=infra destroy` to "start over" unless you mean it: it deletes your service, and the Foundry account then needs a purge before you can recreate it.
