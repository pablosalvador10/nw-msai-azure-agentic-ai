# Architecture Overview

## The Problem

You're a graduate student juggling research, coursework, and job applications. You need an assistant that can:

- **Analyze documents** — summarize papers, extract key insights from readings
- **Crunch numbers** — run statistical analyses, process datasets
- **Keep you informed** — send email alerts when deadlines approach or tasks complete

You decide a **single AI agent** can handle all of this. But here's the challenge: some tasks are simple (text processing), while others require real computation (data analysis) or external integrations (email notifications).

**How do you build this?**

## The Solution: One Agent, Multiple Tools

We'll build a **Graduate Research Assistant** — an AI agent hosted in **Azure AI Foundry** that can:

| Capability | Implementation | Why? |
|------------|----------------|------|
| Summarize text, answer questions | **In-process function** | Simple, runs inside the agent |
| Analyze data, call external APIs | **Azure Function** | Needs compute, scales independently |
| Send emails, trigger workflows | **Logic App** | Built-in connectors, no code needed |

The key insight: **the agent lives in the cloud (Azure AI Foundry), but its tools can live anywhere**. Some tools run inside the agent, others run as independent cloud services.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  Azure AI Foundry Hub                                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐  │
│  │  Azure AI Project                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────────┐  │  │
│  │  │  Azure AI Agent Service                                          │  │  │
│  │  │  ┌────────────────────────────────────────────────────────────┐  │  │  │
│  │  │  │  Agent Runtime                                             │  │  │  │
│  │  │  │                                                            │  │  │  │
│  │  │  │                    ┌─────────┐                             │  │  │  │
│  │  │  │                    │  Thread │                             │  │  │  │
│  │  │  │                    └────┬────┘                             │  │  │  │
│  │  │  │                         │                                  │  │  │  │
│  │  │  │                    ┌────▼────┐                             │  │  │  │
│  │  │  │       ┌────────────│  Agent  │────────────┐                │  │  │  │
│  │  │  │       │            └────┬────┘            │                │  │  │  │
│  │  │  │       │                 │                 │                │  │  │  │
│  │  │  │  ┌────▼────┐       ┌────▼────┐       ┌────▼────┐           │  │  │  │
│  │  │  │  │   LLM   │       │ Python  │       │  HTTP   │           │  │  │  │
│  │  │  │  │         │       │ Function│       │  Tool   │           │  │  │  │
│  │  │  │  │ (runs   │       │  Tool   │       │         │           │  │  │  │
│  │  │  │  │ in Azure│       │ (runs   │       │ (calls  │           │  │  │  │
│  │  │  │  │ Foundry)│       │ in-proc)│       │ external│           │  │  │  │
│  │  │  │  └─────────┘       └─────────┘       └────┬────┘           │  │  │  │
│  │  │  │                                          │                 │  │  │  │
│  │  │  └──────────────────────────────────────────┼─────────────────┘  │  │  │
│  │  └─────────────────────────────────────────────┼────────────────────┘  │  │
│  └────────────────────────────────────────────────┼───────────────────────┘  │
└───────────────────────────────────────────────────┼──────────────────────────┘
                                                    │
                                               HTTPS calls
                                                    │
                          ┌─────────────────────────┼─────────────────────────┐
                          │                         │                         │
                     ┌────▼─────────┐         ┌─────▼────────┐                │
                     │    Azure     │         │   Logic App  │                │
                     │   Function   │         │              │                │
                     │              │         │  • send_email│                │
                     │ • analyze    │         │  • notify    │                │
                     │ • process    │         │  • workflows │                │
                     └──────────────┘         └──────────────┘                │
                          │                         │                         │
                          └─────────────────────────┴─────────────────────────┘
                                      External Azure Services
```

### Azure Hierarchy

| Layer | What It Is |
|-------|------------|
| **Azure AI Foundry Hub** | Top-level container for AI resources |
| **Azure AI Project** | Workspace for your application |
| **Azure AI Agent Service** | Managed service that hosts agents |
| **Agent Runtime** | Where your agent executes |

### Agent Components

| Component | Purpose |
|-----------|---------|
| **Thread** | Maintains conversation state and history |
| **Agent** | Orchestrates reasoning and tool calls |
| **LLM** | The model that powers reasoning (GPT, Claude, etc.) |
| **Python Function Tool** | Code that runs in-process inside the agent |
| **HTTP Tool** | Makes external HTTPS calls to other services |

### External Tools (via HTTPS)

| Tool | Runs Where | Use Case |
|------|------------|----------|
| **Azure Function** | Serverless compute | Heavy processing, data analysis |
| **Logic App** | Workflow engine | Email, Slack, integrations |

> **Key insight**: Python Function Tools run *inside* the agent (fast, no network hop). HTTP Tools call *external* services (scalable, independent).

## Why This Architecture?

### Why Azure AI Foundry?

| Benefit | Description |
|---------|-------------|
| **Managed Runtime** | Microsoft handles infrastructure, scaling, security |
| **Built-in Agent Framework** | Use the official SDK (`azure-ai-projects`) |
| **Model Access** | Deploy GPT-4, GPT-4o, or other models easily |
| **Enterprise Ready** | Authentication, monitoring, compliance built-in |

### Why Decouple Tools?

| Benefit | Description |
|---------|-------------|
| **Independent Scaling** | Heavy computation scales separately from the agent |
| **Language Flexibility** | Azure Functions can run Python, Node.js, C#, etc. |
| **Reusability** | Same function can serve multiple agents or apps |
| **Easier Testing** | Test tools in isolation before connecting to agent |
| **Cost Efficiency** | Pay only when tools are invoked |

### When to Use What?

| Tool Type | Use When... | Example |
|-----------|-------------|---------|
| **In-process function** | Simple logic, no external calls | Text formatting, basic calculations |
| **Azure Function** | Need compute, external APIs, or complex processing | Data analysis, API integrations |
| **Logic App** | Need workflows, notifications, or built-in connectors | Email alerts, Slack messages, file operations |

## How It Works

1. **User asks**: "Analyze my survey data and email me the results"

2. **Agent reasons**: "I need to (1) analyze data → Azure Function, (2) send email → Logic App"

3. **Agent calls Azure Function**: 
   - HTTP POST to `https://my-function.azurewebsites.net/api/analyze`
   - Sends the data, receives statistical summary

4. **Agent calls Logic App**:
   - HTTP POST to `https://prod-xx.logic.azure.com/workflows/...`
   - Triggers email workflow with the results

5. **Agent responds**: "Done! I analyzed your data (mean: 4.2, std: 0.8) and sent the results to your email."

## Next Steps

Ready to build? Head to the notebooks:

1. **[Lab 1](../notebooks/lab1_azure_functions.ipynb)** — Create an Azure Function
2. **[Lab 2](../notebooks/lab2_logic_apps.ipynb)** — Create a Logic App  
3. **[Lab 3](../notebooks/lab3_single_agent_tool_calling.ipynb)** — Wire it all together in Azure AI Foundry

### Beyond HTTP Tools: MCP

Once you've mastered HTTP tools, explore **Model Context Protocol (MCP)** for standardized tool discovery:

4. **[Lab 4](../notebooks/lab4_mcp_server_azure_functions.ipynb)** — Build an MCP server with Azure Functions
5. **[Lab 5](../notebooks/lab5_single_agent_mcp_integration.ipynb)** — Connect AI agents to MCP servers
