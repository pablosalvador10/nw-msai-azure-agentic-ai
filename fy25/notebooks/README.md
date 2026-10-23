# Labs

## Part 1: HTTP Tool Pattern

Connect agents to tools via direct HTTP calls.

| Lab | What You Build |
|-----|----------------|
| [Lab 1](lab1_azure_functions.ipynb) | Azure Function as an HTTP tool |
| [Lab 2](lab2_logic_apps.ipynb) | Logic App as an HTTP tool (no code) |
| [Lab 3](lab3_single_agent_tool_calling.ipynb) | AI Agent connected to HTTP tools |

## Part 2: MCP Pattern

Connect agents to tools via the Model Context Protocol.

| Lab | What You Build |
|-----|----------------|
| [Lab 4](lab4_mcp_server_azure_functions.ipynb) | MCP Server using Azure Functions |
| [Lab 5](lab5_single_agent_mcp_integration.ipynb) | AI Agent connected to MCP servers |

## Part 3: Multi-Agent Systems

Orchestrate multiple agents to solve complex tasks collaboratively.

| Lab | What You Build |
|-----|----------------|
| [Lab 6](lab6_multi_agent_orchestration.ipynb) | Multi-agent orchestration patterns |

## Part 4: Operationalization

Add safety controls, testing, and observability to production AI systems.

| Lab | What You Build |
|-----|----------------|
| [Lab 7](lab7_agent_guardrails.ipynb) | Defense-in-depth guardrails for agents |
| [Lab 8](lab8_safety_evaluations.ipynb) | Safety evaluations and red teaming |
| [Lab 9](lab9_tracing_observability.ipynb) | Tracing and observability with OpenTelemetry |

## Learning Path

```
┌─────────────────────────────────────┐     ┌─────────────────────────────────┐
│  Part 1: HTTP Tools                 │     │  Part 2: MCP                    │
│                                     │     │                                 │
│  Lab 1 (Azure Function) ──┐         │     │  Lab 4 (MCP Server)             │
│                           ├─▶ Lab 3 │     │         │                       │
│  Lab 2 (Logic App) ───────┘         │     │         ▼                       │
│                                     │     │  Lab 5 (Agent + MCP)            │
└─────────────────────────────────────┘     └─────────────────────────────────┘
                    │                                   │
                    └───────────────┬───────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────────┐
                    │  Part 3: Multi-Agent Systems        │
                    │                                     │
                    │  Lab 6 (Multi-Agent Orchestration)  │
                    │    • Concurrent Pattern             │
                    │    • Sequential Pattern             │
                    │    • Group Chat Pattern             │
                    │    • Magentic Pattern               │
                    │    • Handoff Pattern                │
                    └──────────────────┬──────────────────┘
                                       │
                                       ▼
                    ┌─────────────────────────────────────┐
                    │  Part 4: Operationalization         │
                    │                                     │
                    │  Lab 7 (Guardrails)                 │
                    │    • Defense-in-depth               │
                    │    • Content safety                 │
                    │    • Jailbreak detection            │
                    │    • Voice/audio patterns           │
                    │                                     │
                    │  Lab 8 (Evaluations)                │
                    │    • Quality metrics                │
                    │    • Safety evaluators              │
                    │    • Red teaming                    │
                    │                                     │
                    │  Lab 9 (Observability)              │
                    │    • OpenTelemetry tracing          │
                    │    • Azure Monitor                  │
                    │    • Custom spans                   │
                    └─────────────────────────────────────┘
```

**Part 1** (Labs 1-3): Build tools as HTTP endpoints, then connect them to an agent.

**Part 2** (Labs 4-5): Build an MCP server, then connect an agent using the MCP protocol.

**Part 3** (Lab 6): Extend single agents into multi-agent systems using orchestration patterns.

**Part 4** (Labs 7-9): Add guardrails, run evaluations, and enable observability before deployment.
