# GitHub Copilot Configuration

This folder contains custom instructions, custom agents and Agent Skills to tailor GitHub Copilot for this project.

## Files Overview

```
.github/
├── copilot-instructions.md    # Always-on coding standards
├── READMEGC.md                # This file
├── agents/                    # FY26 student agents, named after the instructors (pick them in the Chat agent dropdown)
│   ├── pablo.agent.md         # Pablo · Start here (front door; consults the others)
│   ├── pablo-fundamentals.agent.md  # Pablo · Fundamentals
│   ├── pablo-scoring.agent.md # Pablo · Scoring
│   ├── will.agent.md          # Will · Infra and deploy
│   └── arvind.agent.md        # Arvind · Data
└── skills/                    # Agent Skills (loaded on demand)
    ├── fy26-setup-environment/
    ├── fy26-harness/
    ├── fy26-deploy/
    ├── fy26-troubleshooting/
    ├── fy26-labs/
    ├── fy26-submit-checklist/
    ├── fy26-website/
    ├── fy26-data/
    ├── agentic-ai/            # FY25 (archived)
    ├── azure-functions/       # FY25 (archived)
    ├── mcp-server/            # FY25 (archived)
    ├── notebook-development/  # Instructors: writing lab notebooks
    └── python-testing/        # FY25 (archived)
```

## FY26: help for students

Stuck? Open Copilot Chat, open the Agent dropdown, and pick **Pablo · Start here**. It finds where you are (setup, week, deployed or not), gives you one next step, and names the agent who takes it from there, or asks that agent for you. The student guide, with drawings, example prompts and a section on vibe coding with Copilot's Agent, is [Your course agents](../fy26/foundations/docs/agents.html).

Five agents, one job each, named after the instructor who leads that part of the course: Pablo for the AI and how students are scored, Will for infrastructure and deployment, Arvind for data. Each one says in its first reply that it is the course's AI assistant, not the instructor.

| Agent | Use it when | Skills it loads | Can it change things? |
|---|---|---|---|
| **Pablo · Start here** | You are lost, you do not know the next step, or a question spans two areas | None of its own; it asks the experts | No: checks where you are, consults the other four as subagents, and names one next step |
| **Pablo · Fundamentals** | An AI concept, a lecture, a lab part, the exercise, a failing check to fix, a change to vibe code with Copilot's Agent | `fy26-labs`, `fy26-harness` | No file edits: explains and gives hints; the graded code is yours |
| **Pablo · Scoring** | What a score or check means, how grading works, the course website and Score your deployed service, "Am I ready to submit?" | `fy26-harness`, `fy26-submit-checklist`, `fy26-website`, `fy26-labs` | No: read-only; runs tests and the harness and reports PASS or FAIL |
| **Will · Infra and deploy** | Installing tools, `uv sync`, the kernel, `az login`, Terraform, `.env`, Container Apps, deploying, a broken URL, logs, rollback, the Week 10 API key | `fy26-setup-environment`, `fy26-deploy`, `fy26-troubleshooting` | Runs setup and deploy commands and edits `infra/`, always asking before it changes Azure |
| **Arvind · Data** | The handbook and station data, the harness datasets, patterns across your failing checks, retrieval quality, evaluation metrics, telemetry and KQL, tokens and cost | `fy26-data`, `fy26-harness` | No: read-only analysis, with the query so you can rerun it |

They can ask each other as subagents (the `agents:` list in each file), so a question that spans two areas still gets one answer. Students can ask for it directly: "Ask Will whether my deployed version matches my code."

**Official docs through MCP.** [`fy26/.mcp.json`](../fy26/.mcp.json) (and the copy at the repository root) adds Microsoft Learn's MCP server, `microsoftLearn`, which all five agents use to search and fetch current Microsoft documentation. It needs no sign-in. The first time, VS Code may ask you to trust or start the server: allow it.

**Vibe coding.** The course agents do not write graded code. Copilot's built-in **Agent** does, guided by [`fy26/AGENTS.md`](../fy26/AGENTS.md); in Week 8 directing it is the exercise (`nearest_station_with_docks`). Pablo · Fundamentals coaches the prompt and the review.

The skills also work without picking an agent: type `/` in chat (for example `/fy26-troubleshooting`), or just ask, and Copilot loads the matching skill.

**Handoff buttons** (`handoffs:` in each agent file) appear when the chat session runs in VS Code's Local harness. In Copilot sessions they do not; students pick the named agent from the Agent dropdown instead.

**Opened only the `fy26/` folder?** VS Code then looks for agents in `fy26/` only. [`fy26/.vscode/settings.json`](../fy26/.vscode/settings.json) turns on `chat.useCustomizationsInParentRepositories` so the agents and skills here are found. VS Code applies that setting only in a trusted workspace, so trust the folder and its parent when asked. If they still do not appear, enable that setting in your User settings, or open the repository root instead.

## Custom Instructions

**File:** `copilot-instructions.md`

These instructions are **always applied** to every Copilot interaction in this repository, including students' chats. They describe:
- The repository layout (`fy26/` current, `fy25/` archived) and the commands to run from `fy26/`
- Python standards (3.12, type hints, Ruff, Pydantic) and the rules for the service in `fy26/app/` (fixed contract, business rules in `domain.py`, keyless Azure access)
- Security: never commit `.env`, tfvars, state or harness reports
- The teaching context and voice for graduate students

## Agent Skills

Skills are **loaded on-demand** when relevant to your prompt.

| Skill | When Copilot Uses It |
|-------|---------------------|
| `fy26-setup-environment` | FY26 setup: tools, `uv sync`, kernel, `az login`, Terraform, `.env`, first deploy |
| `fy26-harness` | Running the harness, reading reports and proofs, debugging a failing check |
| `fy26-deploy` | `course.deploy()`, revisions, logs, rollback, Terraform changes, API key, KQL |
| `fy26-troubleshooting` | Any FY26 error message: symptom, cause, fix |
| `fy26-labs` | Week-by-week map: what to build, which file, which checks |
| `fy26-submit-checklist` | Ready to submit? |
| `fy26-data` | The handbook, stations and harness datasets; reports and proofs; analysis recipes; evaluation metrics; KQL |
| `azure-functions` | FY25 (archived): Azure Functions |
| `mcp-server` | FY25 (archived): MCP on Azure Functions |
| `python-testing` | FY25 (archived): pytest for Azure Functions |
| `agentic-ai` | FY25 (archived): agents with tool calling |
| `notebook-development` | Instructors: creating teaching lab notebooks |

### Enable Skills

Skills are on by default (`chat.useAgentSkills`). If the `fy26-` skills do not appear when you type `/` in chat, open Settings (`Cmd+,`), search `chat.useAgentSkills`, and turn it on.

### How Skills Work

1. **Discovery** - Copilot reads skill names/descriptions (lightweight)
2. **Loading** - When your prompt matches, the full `SKILL.md` loads
3. **Resources** - Additional files in skill folders load as needed

## Adding a New Skill

1. Create a folder: `.github/skills/my-skill/`
2. Add `SKILL.md` with this format:

```markdown
---
name: my-skill
description: When to use this skill (helps Copilot decide)
---

# Skill Title

Instructions, patterns, and examples...
```

3. Optionally add scripts, templates, or examples to the folder

## Testing Your Setup

Ask Copilot in Agent Mode:
- "How do I run the harness for Week 6?" → Should use `fy26-harness` skill
- "terraform apply fails with InsufficientQuota" → Should use `fy26-troubleshooting` skill
- "Which file do I change for Week 7?" → Should use `fy26-labs` skill
- "Which ticket categories does my service confuse?" → Should use `fy26-data` skill
- "Create a new lab notebook" → Should use `notebook-development` skill

Then try each agent from the dropdown:

- **Pablo · Start here**, "I am lost": it says it is the course's AI assistant, checks your setup, and replies with where you are, one next step and who takes it from there.
- **Pablo · Start here**, "Week 6. My laptop scores 78 but my URL scores 41. Ask Will whether the deployed version matches my code": it consults Will as a subagent and combines the answer.
- **Pablo · Fundamentals**, "Week 6, `w06.ask.citations` is PART. First hint only": it reads the newest report and gives one hint, not the code.
- **Pablo · Scoring**, "Week 5. How is my score computed?": it shows the weighted average and the weight of each check.
- **Will · Infra and deploy**, "My deploy timed out waiting for the new revision": it reads revisions and logs before suggesting anything, and asks before changing Azure.
- **Arvind · Data**, "What is in the Week 6 dataset?": it opens `harness/data/week06.jsonl`, explains the fields, and shows the command it used.

In a Local session each reply also offers handoff buttons to the related agents.

The offline test [`fy26/tests/test_course_agents.py`](../fy26/tests/test_course_agents.py) checks the agent and skill files: frontmatter, tool names, MCP servers, handoff targets, skill names, links, and that the commands, files and check ids they cite exist.

## Resources

- [Custom agents in VS Code](https://code.visualstudio.com/docs/agent-customization/custom-agents)
- [Custom agent file reference](https://code.visualstudio.com/docs/agents/reference/custom-agent-file-reference)
- [Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [Customizations in a monorepo (parent repository discovery)](https://code.visualstudio.com/docs/agent-customization/overview#_use-customizations-in-a-monorepo)
- [Choose an agent harness (Copilot or Local)](https://code.visualstudio.com/docs/agents/run/agent-harnesses)
- [Custom agents configuration (tool aliases)](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
- [Custom Instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
- [Agent Skills Standard](https://agentskills.io)
