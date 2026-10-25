# Setup · Your course environment

Do this once, before Week 5. Allow about 45 minutes if the tools are installed and Azure access is ready; quota or permission requests can take longer. At the end you have, in your own Azure resource group:

- a **Microsoft Foundry** resource with a project and two models (chat and embeddings),
- an **Azure Container Registry** for your images,
- an **Azure Container Apps** environment running your service at a public HTTPS URL,
- **Application Insights** collecting logs and traces,
- one **managed identity** that lets the service call the models with no keys or passwords.

All of it is created by Terraform from the files in [`infra/`](../infra/README.md), driven from [`setup.ipynb`](setup.ipynb).

**New to all of this?** That is expected. Do the steps in order, and when one fails, do not start over: open Copilot Chat in VS Code, pick **Will · Infra and deploy**, and paste the error. [Your course agents](../foundations/docs/agents.html) shows how, and it works as soon as you have cloned the course (step 2).

## 1. Install the tools

| Tool | Why | Install | Check |
|---|---|---|---|
| VS Code + Python and Jupyter extensions | Editor and notebooks | [code.visualstudio.com](https://code.visualstudio.com/) | |
| GitHub Copilot in VS Code | The course agents that help you when you are stuck | [Set up Copilot in VS Code](https://code.visualstudio.com/docs/setup/copilot); students: [Copilot Student](https://docs.github.com/en/copilot/how-tos/manage-your-account/free-access-with-copilot-student) is free | The Agent dropdown in Chat lists the FY26 agents |
| uv | Python and packages, one command | [docs.astral.sh/uv](https://docs.astral.sh/uv/getting-started/installation/) | `uv --version` |
| Azure CLI | Sign in, build images, inspect resources | [Install the Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli) | `az version` |
| Terraform | Create the infrastructure | [Install Terraform](https://developer.hashicorp.com/terraform/install) | `terraform -version` |
| Git | Get the course and keep your work | [git-scm.com](https://git-scm.com/downloads) | `git --version` |

You do **not** need Docker: images are built in Azure (`az acr build`).

## 2. Get the course and its Python environment

Open a terminal: **Terminal** on macOS, **PowerShell** on Windows, or, once VS Code is installed, **Terminal > New Terminal** inside VS Code. Then run:

```bash
git clone https://github.com/pablosalvador10/northwestern-msai-azure-agentic-ai.git
cd northwestern-msai-azure-agentic-ai/fy26
uv sync
```

`uv sync` reads `pyproject.toml` and `uv.lock`, downloads Python 3.12 if needed, and creates `fy26/.venv` with the exact package versions everyone uses. On Windows, run the same three commands in PowerShell.

Open the `fy26` folder in VS Code, open `setup/setup.ipynb`, and choose the kernel **`.venv (Python 3.12)`** from `fy26/.venv` (on Windows it may show as `.venv\Scripts\python.exe`). If the kernel is not listed, run **Python: Select Interpreter** from the Command Palette, pick `fy26/.venv`, and reopen the notebook.

## 3. Azure access you need

- For the default setup, you need permission to create a resource group and its resources, register resource providers, and assign roles. **Owner**, or **Contributor** plus **Role Based Access Control Administrator**, at subscription scope covers those operations. Contributor alone cannot assign roles.
- If the class provides an existing resource group, ask for its name and confirm that its providers and access permissions are ready. In the notebook's section 3, set `RESOURCE_GROUP` to that name; the notebook then tells Terraform to use the group instead of creating one. Access only to that group does not let you create a new group at subscription scope. In the class subscription the group is named like `<netid>_resourcegroup`, and Azure Policy allows US regions only.
- The region must offer the models in [`infra/variables.tf`](../infra/variables.tf), with quota for your subscription. The notebook picks it from the last digit of your NetID: 0 to 4 use `eastus2`, 5 to 9 use `eastus`. The class is split because a subscription holds at most 50 Container Apps environments per region. Both regions are tested with every lab. Change the region only if an instructor asks you to.

If the class provides your subscription, confirm these prerequisites with the instructor before you begin.

## 4. Run the notebook

Open [`setup.ipynb`](setup.ipynb) and run it top to bottom. It signs you in, writes your Terraform settings, creates the resources, deploys the service and runs the harness. Read the Terraform plan before applying it. Provisioning and the first image build each take several minutes; a delay is not a reason to delete everything and start again.

## If something goes wrong

Find your error below, or ask for help in VS Code: open Copilot Chat, pick **Will · Infra and deploy** in the Agent dropdown, and paste the error. Will checks each setup step with you and explains the fix. New to the agents? [Your course agents](../foundations/docs/agents.html) shows how to use them in five minutes.

| Symptom | Cause | Fix |
|---|---|---|
| `AuthorizationFailed` on `azurerm_role_assignment` | You are Contributor only | Ask for Owner or RBAC Administrator on the subscription or resource group |
| `InsufficientQuota` or `DeploymentModelNotSupported` | The deployment type, model, region or requested capacity is unavailable to your subscription | Ask the instructor to check quota and availability. Review a new Terraform plan before changing region or capacity; moving an existing resource can replace it |
| `MissingSubscriptionRegistration` | A resource provider is not registered | `az provider register -n Microsoft.App` (or the namespace in the error), wait 2 minutes, apply again |
| First model call returns 401 or 403 | Role assignments take a few minutes to propagate | Wait two minutes and rerun the cell; it can take up to ten |
| The URL answers slowly the first time | The app scaled to zero while idle | Normal. The first request takes about 30 to 45 seconds |
| `az login` picks the wrong tenant | Several accounts or directories | `az login --tenant <tenant-id>` then `az account set --subscription <id>` |
| `uv sync`, `az` or `terraform init` fail with certificate or proxy errors | A corporate proxy inspects HTTPS | Try another network (a phone hotspot is enough); or set `HTTPS_PROXY` and install the proxy's root certificate, as your IT team documents |
| `apply` after a `destroy` fails: the Foundry name is taken or soft-deleted | Deleted Foundry accounts are kept for a while | `az cognitiveservices account purge -n <name> -g <resource group> -l <location>`, then apply again |

## Cost and clean-up

The app scales to zero when idle, but that does not make the resource group free. Model calls, image builds, the container registry and retained logs can incur charges. Check the costs in your own subscription; usage, region and pricing determine the bill.

**Clean up only after grading is complete.** Destroying the Terraform-managed resources removes the deployed service and may delete its images and logs. If Terraform created the resource group, deleting that group also deletes anything else placed in it. Keep unrelated work in another group, save any evidence you need, and check the destruction plan before confirming. Do not use `destroy` to troubleshoot a failed step.

When you are ready, run the following from the cohort folder and review the confirmation prompt:

```bash
terraform -chdir=infra destroy
```

## Learn more

- [Terraform on Azure (Microsoft Learn)](https://learn.microsoft.com/en-us/azure/developer/terraform/)
- [Get started with Terraform on Azure (HashiCorp)](https://developer.hashicorp.com/terraform/tutorials/azure-get-started)
- [uv: working on projects](https://docs.astral.sh/uv/guides/projects/)
- [Create Azure resources using the Azure CLI (Learn module)](https://learn.microsoft.com/en-us/training/modules/create-azure-resources-by-using-azure-cli/)
