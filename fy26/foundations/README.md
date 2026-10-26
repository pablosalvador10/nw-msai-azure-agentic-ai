# Foundations · Start here

Two things to have before Week 5: a way to get help when you are stuck, and enough of each tool to follow the labs.

## 1. Your course agents

VS Code's Copilot Chat has five agents for this course, each with one job. Start with **Pablo · Start here** whenever you are lost: it finds where you are, gives you one next step, and asks the experts for you when your question needs them. **Pablo · Fundamentals** teaches the AI and coaches the labs; **Pablo · Scoring** explains your score, how grading works and the course website, and runs the check before you submit; **Will · Infra and deploy** handles setup, Azure, Terraform and deployment; **Arvind · Data** handles the course data, your harness reports, evaluation and telemetry.

**Read first:** [docs/agents.html](docs/agents.html) shows how to open them, which one to ask when, how to call them (including asking Pablo to consult the others), how to vibe code with Copilot's Agent, and what they will and will not do. It takes about ten minutes, and you need only the cloned course, not a finished setup.

## 2. The tools, one at a time

The weekly labs use five tools you may not have met before. Each primer below is a short notebook: what the tool is, why we use it, and a few cells you run to see it work. Do the ones you need before the session where they first appear.

**Read them in the browser:** [docs/primers.html](docs/primers.html) has all five primers on one page, with a contents column on the left and the code each notebook runs.

| Primer | You need it from | What you will be able to do | Time |
|---|---|---|---|
| [Terraform](terraform.ipynb) | Setup | Read our `infra/` files, run plan and apply, change a resource safely | 20 min |
| [FastAPI](fastapi.ipynb) | Week 5 | Build an HTTP API with validated JSON, test it without a server | 20 min |
| [Containers and Container Apps](containers.ipynb) | Week 5 | Explain an image, read our Dockerfile, inspect revisions and logs | 15 min |
| [Identity and access](identity.ipynb) | Week 5 | Explain how the app calls Foundry without keys; read a token; list role assignments | 15 min |
| [The harness](harness.ipynb) | Week 5 | Run the harness, read a report, write your own check | 15 min |

Each primer runs from `fy26/` with the course environment (`uv sync`). The Terraform, containers and identity primers need the resources from [Setup](../setup/README.md).

## Also useful

| Topic | Where to learn it |
|---|---|
| Python environments with uv | [uv: working on projects](https://docs.astral.sh/uv/guides/projects/) |
| Git and GitHub | [GitHub Foundations (Microsoft Learn)](https://learn.microsoft.com/en-us/training/paths/github-foundations/) |
| Azure CLI | [Create Azure resources using the Azure CLI](https://learn.microsoft.com/en-us/training/modules/create-azure-resources-by-using-azure-cli/) |
| Containers, conceptually | [What is a container? (Docker)](https://docs.docker.com/get-started/docker-concepts/the-basics/what-is-a-container/) |
| Container Apps, end to end | [Deploy cloud-native apps using Azure Container Apps (Learn path)](https://learn.microsoft.com/en-us/training/paths/deploy-cloud-native-applications-to-azure-container-apps/) |
| FastAPI, in depth | [FastAPI tutorial](https://fastapi.tiangolo.com/tutorial/) |
| Terraform, in depth | [Get started with Terraform on Azure (HashiCorp)](https://developer.hashicorp.com/terraform/tutorials/azure-get-started) |
