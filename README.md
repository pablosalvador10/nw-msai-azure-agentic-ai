# Agentic AI on Microsoft Foundry

A hands-on course in building AI agents that hold up in production. You build one service, a support API for **Lakeshore Ride** (a fictional bike-share company), and give it a new capability each week: structured output, retrieval with citations, tools, several agents working together, MCP, and the guardrails a public service needs. Every week ends the same way: the service runs on Azure and a test harness scores it, so you always know what works and what to fix next.

Each topic starts from first principles in plain Python, so you see what a framework does before you use one.

## What you will build

| Week | Topic | Your service gains |
|---|---|---|
| 5 | [Fundamentals of Azure AI](fy26/week05-fundamentals-of-azure-ai/README.md) | `POST /v1/classify` and `/v1/chat`: ticket triage with structured output |
| 6 | [RAG and tool calling](fy26/week06-rag-and-tool-calling/README.md) | `POST /v1/ask`: answers from the handbook, with citations and tools |
| 7 | [Multi-agent systems](fy26/week07-multi-agent-systems/README.md) | `POST /v1/resolve`: specialist agents, actions and approvals |
| 8 | [Harnesses and agentic coding](fy26/week08-harnesses-and-agentic-coding/README.md) | `/mcp`: your tools for any agent, plus a feature built with a coding agent |
| 10 | [Production agentic systems](fy26/week10-production-agentic-systems/README.md) | Guardrails, limits, an API key and tracing on every route |

Every week has a lecture to read, slides, a main lab (the exercise) and an optional deep dive.

**Built with:** models on Microsoft Foundry through the Responses API, Microsoft Agent Framework, MCP, FastAPI on Azure Container Apps, Terraform and OpenTelemetry. The [course README](fy26/README.md#the-stack-as-of-october-2026) lists the versions.

## What you need

- An **Azure subscription** where you can create a resource group, register resource providers and assign roles (Owner, or Contributor plus Role Based Access Control Administrator).
- **VS Code**, **uv**, the **Azure CLI**, **Terraform** and **Git**. No Docker: images are built in Azure.
- Optional: **GitHub Copilot** in VS Code, for the course agents that help when you are stuck.

Running the service costs money: model calls, image builds, the container registry and logs. The app scales to zero when idle. [Setup](fy26/setup/README.md) explains the cost and how to clean up.

## Get started

1. **Clone the course and install its Python environment.**

   ```bash
   git clone https://github.com/pablosalvador10/nw-msai-azure-agentic-ai.git
   cd nw-msai-azure-agentic-ai/fy26
   uv sync
   ```

2. **Open the [course home](fy26/index.html) in your browser**, from your clone (GitHub shows HTML files as source). It links setup, the Foundations primers, and every lecture, slide deck and lab.
3. **Do [Setup](fy26/setup/README.md) once**, before Week 5: sign in to Azure, create your resources with Terraform, and deploy the starter service.
4. **Stuck?** In VS Code, open Copilot Chat and pick **Pablo · Start here** from the Agent dropdown. [Your course agents](fy26/foundations/docs/agents.html) explains all five.

The [course README](fy26/README.md) describes the weekly routine and how the harness scores your service.

## What is in this repository

```
fy26/          The course: home page, setup, foundations, one folder per week,
               the service (app/), the harness, Terraform (infra/) and tests
fy25/          The previous edition, kept as taught
.github/       Continuous integration, and the Copilot agents and skills for the course
```

The [previous edition](fy25/README.md) is kept for reference and is no longer updated; the cloud services and links it uses may have changed.

## License

MIT, see [LICENSE](LICENSE). Found a mistake? Open an issue; the [contributor guide](CONTRIBUTING.md) explains how the course is built and tested.
