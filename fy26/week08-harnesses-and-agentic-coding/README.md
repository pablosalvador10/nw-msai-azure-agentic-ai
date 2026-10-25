# Week 8 · Harnesses and Agentic Coding

**Date:** Nov 17 · **Instructors:** Will, Pablo, Arvind · **Notes:** [lecture.md](lecture.md) · **Lecture page:** [lecture.html](docs/lecture.html) · **Slides:** [slides.html](docs/slides.html) · **Lab:** [lab.ipynb](lab.ipynb) · **Submit:** one URL, before the Week 10 session

[← Week 7](../week07-multi-agent-systems/README.md) · [FY26 home](../README.md) · [Next: Week 10 →](../week10-production-agentic-systems/README.md)

| In this folder | What it is |
|---|---|
| `README.md` | Start here: goals, preparation, the exercise and how it is graded |
| [`lecture.md`](lecture.md) | The lecture notes: the content of the session |
| [`lab.ipynb`](lab.ipynb) | Required: the lab you run in class; it ships the service you submit |
| [`deep-dive.ipynb`](deep-dive.ipynb) | Optional, not graded, for after you submit: the notes in more depth, with code |
| [`docs/lecture.html`](docs/lecture.html) | The notes as one page with a contents column; prints to PDF |
| [`docs/slides.html`](docs/slides.html) | The notes as slides for the session |

## Why this week matters

A model on its own only produces text. What makes it an *agent* is the **harness** around it: the loop that calls tools, the context it is given, the permissions it has, and the checks that tell it whether it succeeded. Coding agents such as GitHub Copilot, Claude Code and Codex are harnesses built for software. This week you look at harnesses from both sides: you **publish your service's tools** to any agent through the Model Context Protocol (MCP), and you **use a coding agent** to build a feature against a specification written as tests, verified by your own harness.

## By the end you can

- Name the parts of an agent harness: loop, tools, context, permissions, verification; and tell an agent harness from an evaluation harness.
- Explain MCP, including why its current revision (2026-07-28) is stateless, and expose your service's tools at `/mcp` to any MCP client.
- Call those tools from an MCP client, from an Agent Framework agent, and from VS Code.
- Run the service locally and test it end to end before you deploy.
- Use a coding agent effectively: repository instructions (`AGENTS.md`), a spec as tests, small steps, review of every diff.

## Before class (about 1 hour)

1. Your Week 7 service is deployed and scores in the harness.
2. Read [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) (Anthropic).
3. Read [What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/docs/getting-started/intro).
4. Make sure a coding agent works in your VS Code: GitHub Copilot in agent mode, or another coding agent you prefer (Claude Code, Codex).

## Lecture notes

The content of the session is in **[lecture.md](lecture.md)**: evaluation harnesses versus agent harnesses, the anatomy of a harness, context engineering, **MCP** (features, the stateless 2026-07-28 revision on the wire, security, and where it appears across Azure), coding agents in 2026 with **GitHub Copilot** (instructions, prompt files, custom agents, skills, hooks, the cloud agent) and **OpenAI Codex** (sandbox and approvals, `AGENTS.md`, `codex exec`), Agent Framework's harness agent, driving and hosting agents with **Microsoft Foundry**, spec-driven development, and the security of agentic coding. The lab follows the same order.

## The exercise

**Service:** `POST /mcp` is a Model Context Protocol endpoint (JSON-RPC over HTTP, revision 2026-07-28, stateless) that publishes `search_handbook`, `quote_fare` and `get_station` ([`app/mcp_server.py`](../app/mcp_server.py)).

**Your job:** with a coding agent, add a fourth tool, `nearest_station_with_docks`, and publish it over MCP. The specification is a set of tests in [`tests/test_week08_nearest_station.py`](../tests/test_week08_nearest_station.py): they are skipped until the function exists, then they must pass. In short:

- Input: a station id. Output: the closest **other** station that is **open** and has **at least one free dock**.
- Distance is great-circle (haversine) distance; `app/domain.py` already has `distance_km`.
- Return `{"station_id", "name", "distance_km", "docks_available"}`. An unknown id returns `{"error": ...}`.

The coding agent writes the code. You write the prompt, review every change, run the tests and the harness, and decide what ships. When the tests pass and the tool is published at `/mcp`, the local harness shows 100.

| Check | Weight | What it measures |
|---|---|---|
| `core.health`, `core.info` | 1 + 1 | The service is up and identifies you |
| `w08.mcp.discover` | 1 | The server answers `server/discover` and supports revision 2026-07-28 |
| `w08.mcp.tools` | 2 | The three course tools are published, with input schemas |
| `w08.mcp.call` | 3 | Tool calls return the right data |
| `w08.mcp.new_tool` | 3 | `nearest_station_with_docks` exists and answers correctly |

**Stuck?** This week the coding agent that writes `nearest_station_with_docks` is Copilot's built-in **Agent**, guided by [`AGENTS.md`](../AGENTS.md); [Vibe coding with Copilot's Agent](../foundations/docs/agents.html#vibe) shows the loop and a prompt template. **Pablo · Fundamentals** coaches your prompt and your review of the diff, and explains any failing `w08.mcp.*` check. **Arvind · Data** explains the station data your new tool reads, and **Will · Infra and deploy** helps you deploy and fixes MCP connection errors. Before the deadline, ask **Pablo · Scoring** "Am I ready to submit?". New to the agents? Read [Your course agents](../foundations/docs/agents.html).

## The deep dive (optional)

[`deep-dive.ipynb`](deep-dive.ipynb) is for after you submit. It is not graded, and it does not edit `app/` or deploy, so it cannot change your score. Its six parts go under the hood: MCP on the wire, schemas and descriptions as prompts and as an attack surface, a harness agent, a Foundry agent with a remote MCP server, and the context a coding agent reads here ([list of parts](docs/lecture.html#deep-dive)). Same setup as the lab; run the parts in order. Cost: a few cents.

## Go further in your service (optional)

Ideas beyond the exercise, mostly in your own service. If one changes `app/`, score it in-process before you deploy it.

- Connect a second MCP server to the same agent, for example [Microsoft Learn's](https://learn.microsoft.com/api/mcp), and ask a question that needs both.
- Publish the handbook pages as MCP **resources**, so a client can read a page without calling a model.
- Ask your coding agent to write a new harness check for the new tool's error case, then review it as you would a colleague's pull request.
- Improve `AGENTS.md` with one rule you wish the agent had followed. Did the next run follow it?

## Microsoft Learn and further reading

| Topic | Resource |
|---|---|
| Coding agents in VS Code | [Building Applications with GitHub Copilot Agent Mode](https://learn.microsoft.com/en-us/training/modules/github-copilot-agent-mode/) (module) |
| MCP tools with Foundry agents | [Integrate MCP Tools with Azure AI Agents](https://learn.microsoft.com/en-us/training/modules/connect-agent-to-mcp-tools/) (module) |
| Add an MCP server to VS Code | [Add MCP servers in VS Code](https://code.visualstudio.com/docs/copilot/customization/mcp-servers) |
| MCP itself | [What is the Model Context Protocol (MCP)?](https://modelcontextprotocol.io/docs/getting-started/intro) · [What changed in 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28/changelog) |
| The MCP Python SDK used in `app/mcp_server.py` | [MCP Python SDK](https://py.sdk.modelcontextprotocol.io/) · [Add to an existing app](https://py.sdk.modelcontextprotocol.io/run/asgi/) · [Clients](https://py.sdk.modelcontextprotocol.io/client/) |
| Harness design | [Effective harnesses for long-running agents (Anthropic)](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) · [Harness engineering (OpenAI)](https://openai.com/index/harness-engineering/) |
| An agent harness in Agent Framework | [Agent harness](https://learn.microsoft.com/en-us/agent-framework/concepts/harness) |
| Evaluating agents: vocabulary and method | [Demystifying evals for AI agents (Anthropic)](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents) |
| Working with a coding agent | [Claude Code best practices](https://code.claude.com/docs/en/best-practices) |
| Context for agents | [Effective context engineering for AI agents (Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| Repository instructions for agents | [AGENTS.md](https://agents.md) · [Agent Skills (Anthropic)](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview) |
| Building your own coding-style agent | [Agent SDK overview (Anthropic)](https://code.claude.com/docs/en/agent-sdk/overview) |
