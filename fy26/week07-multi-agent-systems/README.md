# Week 7 · Multi-Agent Systems

**Date:** Nov 10 · **Instructors:** Pablo, Will · **Notes:** [lecture.md](lecture.md) · **Lecture page:** [lecture.html](docs/lecture.html) · **Slides:** [slides.html](docs/slides.html) · **Lab:** [lab.ipynb](lab.ipynb) · **Submit:** one URL, before the Week 8 session

[← Week 6](../week06-rag-and-tool-calling/README.md) · [FY26 home](../README.md) · [Next: Week 8 →](../week08-harnesses-and-agentic-coding/README.md)

| In this folder | What it is |
|---|---|
| `README.md` | Start here: goals, preparation, the exercise and how it is graded |
| [`lecture.md`](lecture.md) | The lecture notes: the content of the session |
| [`lab.ipynb`](lab.ipynb) | Required: the lab you run in class; it ships the service you submit |
| [`deep-dive.ipynb`](deep-dive.ipynb) | Optional, not graded, for after you submit: the notes in more depth, with code |
| [`docs/lecture.html`](docs/lecture.html) | The notes as one page with a contents column; prints to PDF |
| [`docs/slides.html`](docs/slides.html) | The notes as slides for the session |

## Why this week matters

One agent with every tool and a two-page prompt works until it does not: it mixes up responsibilities, calls tools it should not, and becomes impossible to debug. Splitting the work among **specialists**, each with its own instructions and only the tools it needs, gives you clearer behavior, parallel work and least privilege. It also costs more calls, more latency and more ways to fail. This week is about when to split, how to orchestrate, and how to prove the split paid off.

## By the end you can

- Decide between one agent, a fixed workflow and a multi-agent team, and justify it with cost: calls, tokens, latency, compounding errors.
- Name the main orchestration patterns (sequential, concurrent, agent as tool, handoff, group chat, manager-led) and when each fits.
- Build sequential and concurrent workflows with **Microsoft Agent Framework**.
- Route work with a **triage agent** that returns structured output.
- Give each agent **least privilege**: only the tools its job needs; require **human approval** for actions that move money.
- Measure a multi-agent system on correctness of **actions**, not just prose.

## Before class (about 1 hour)

1. Your Week 6 service is deployed and scores in the harness.
2. Read [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents) (Anthropic). Note the difference between *workflows* and *agents*.
3. Skim the Learn module [Orchestrate a multi-agent solution using the Microsoft Agent Framework](https://learn.microsoft.com/en-us/training/modules/orchestrate-semantic-kernel-multi-agent-solution/).

## Lecture notes

The content of the session is in **[lecture.md](lecture.md)**, a deep tour of **Microsoft Agent Framework**: when to split an agent, the agent abstraction (sessions, context providers, agents as tools), middleware, graph workflows (executors, typed edges, supersteps, switch-case routing, fan-out and fan-in), checkpoints and human-in-the-loop, the five orchestrations (sequential, concurrent, handoff, group chat, Magentic), least privilege for teams, cost and latency, evaluation, and running agents on Foundry, A2A and AG-UI. The lab follows the same order.

## The exercise

**Service:** `POST /v1/resolve` takes a support case and returns a `resolution` for the rider, the `route` of agents that worked on it, and the `actions` they took: ride credits and maintenance tickets ([contract](../app/contract.py)).

**Starting point:** [`app/services/resolve.py`](../app/services/resolve.py) sends every case to every specialist (policy, billing, operations) in parallel, then a writer drafts the reply. It works, but it is slow, and specialists act on cases that are not theirs.

**Your job:** add a triage agent that picks only the specialists a case needs, tighten each specialist's instructions, and make the credits exactly right. Credits are money: the harness checks the amount, the rider and the status. 100 on the public cases is reachable: the harness names every case that missed and what your service did.

| Check | Weight | What it measures |
|---|---|---|
| `core.health`, `core.info` | 1 + 1 | The service is up and identifies you |
| `w07.resolve.schema` | 1 | Every response matches the contract |
| `w07.resolve.route` | 2 | Cases reach the right specialists, and no others |
| `w07.resolve.actions` | 3 | Credits (rider, amount, status) and tickets (category, station) are correct; no unowed credit |
| `w07.resolve.answer` | 1 | Replies state the key facts |
| `w07.latency` | 1 | Median latency at or under 20 s, scaled by valid responses |

**Stuck?** In Copilot Chat, pick **FY26 Lab Tutor** and name the check, for example: "Week 7, `w07.resolve.actions` is PART. What do the failing cases have in common? First hint only." It explains and hints; the code stays yours. **FY26 Deploy Doctor** helps you ship, **FY26 Submit Check** checks you before the deadline. New to the agents? Read [Your course agents](../foundations/docs/agents.html).

## The deep dive (optional)

[`deep-dive.ipynb`](deep-dive.ipynb) is for after you submit. It is not graded, and it does not edit `app/` or deploy, so it cannot change your score. Its eight parts take Agent Framework apart: workflows, routing, middleware, checkpoints, orchestration patterns, the cost of a team, and evaluation ([list of parts](docs/lecture.html#deep-dive)). Same setup as the lab; run the parts in order. Cost: a few cents of model calls.

## Go further in your service (optional)

Ideas beyond the exercise, mostly in your own service. If one changes `app/`, score it in-process before you deploy it.

- Replace the fixed fan-out with a **handoff** workflow (`HandoffBuilder`): triage hands the case to one specialist, who can hand it on. Compare route accuracy and latency.
- Rebuild the team as **agents as tools** (`agent.as_tool()`): one resolver keeps control and calls specialists like functions.
- Add a **verifier**: an agent that checks every proposed credit against the policy before the writer runs. Does it catch errors or add new ones?
- From the proof in `reports/`, compute the latency per case. Which cases are slow, and why?

## Microsoft Learn and further reading

| Topic | Resource |
|---|---|
| Orchestration patterns in Agent Framework | [Orchestrate a multi-agent solution using the Microsoft Agent Framework](https://learn.microsoft.com/en-us/training/modules/orchestrate-semantic-kernel-multi-agent-solution/) (module) |
| One agent with tools, in Agent Framework | [Develop an AI agent with Microsoft Agent Framework](https://learn.microsoft.com/en-us/training/modules/develop-ai-agent-with-semantic-kernel/) (module) |
| The whole agents track | [Develop AI Agents on Azure](https://learn.microsoft.com/en-us/training/paths/develop-ai-agents-azure/) (learning path) |
| Agent Framework | [Microsoft Agent Framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview) |
| When (not) to build agents | [Building effective agents (Anthropic)](https://www.anthropic.com/engineering/building-effective-agents) |
| What a multi-agent system costs, measured | [How we built our multi-agent research system (Anthropic)](https://www.anthropic.com/engineering/multi-agent-research-system) |
| Handoffs versus agents as tools | [Agent orchestration (OpenAI)](https://developers.openai.com/api/docs/guides/agents/orchestration) |
| A person in the loop | [Tool approvals in Agent Framework](https://learn.microsoft.com/en-us/agent-framework/agents/tools/tool-approval) |
| Certification, if you want one | [Exam AI-500: Designing and Implementing Multi-Agent AI Solutions](https://learn.microsoft.com/en-us/credentials/certifications/exams/ai-500/) |
