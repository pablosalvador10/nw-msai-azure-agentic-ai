# GitHub Copilot Configuration

This folder contains custom instructions, custom agents and Agent Skills to tailor GitHub Copilot for this project.

## Files Overview

```
.github/
├── copilot-instructions.md    # Always-on coding standards
├── READMEGC.md                # This file
├── agents/                    # FY26 student agents (pick them in the Chat agent dropdown)
│   ├── fy26-guide.agent.md
│   ├── fy26-setup-doctor.agent.md
│   ├── fy26-lab-tutor.agent.md
│   ├── fy26-deploy-doctor.agent.md
│   └── fy26-submit-check.agent.md
└── skills/                    # Agent Skills (loaded on demand)
    ├── fy26-setup-environment/
    ├── fy26-harness/
    ├── fy26-deploy/
    ├── fy26-troubleshooting/
    ├── fy26-labs/
    ├── fy26-submit-checklist/
    ├── agentic-ai/            # FY25 (archived)
    ├── azure-functions/       # FY25 (archived)
    ├── mcp-server/            # FY25 (archived)
    ├── notebook-development/  # Instructors: writing lab notebooks
    └── python-testing/        # FY25 (archived)
```

## FY26: help for students

Stuck? Open Copilot Chat, open the Agent dropdown, and pick **FY26 Guide**. It finds where you are (setup, week, deployed or not), gives you one next step, and names the specialist who takes it from there. The student guide, with drawings and example prompts, is [Your course agents](../fy26/foundations/docs/agents.html).

| Agent | Use it when | Can it change things? |
|---|---|---|
| **FY26 Guide** | You are lost, or do not know what to do next | No: read-only checks, then routes you |
| **FY26 Setup Doctor** | Installing tools, `uv sync`, the kernel, `az login`, Terraform, `.env`, the first deploy | Runs setup commands, asks before changing Azure |
| **FY26 Lab Tutor** | A concept, a lab part, a failing harness check, how to raise your score | No file edits: explains and gives hints; you write the graded code |
| **FY26 Deploy Doctor** | Deploying, a broken URL, revisions, logs, rollback, the Week 10 API key | Deploys and fixes infrastructure, asks first |
| **FY26 Submit Check** | Before every deadline | No: runs the checklist and reports PASS/FAIL |

For Week 8, the coding agent that writes `nearest_station_with_docks` is Copilot's built-in **Agent** mode, guided by [`fy26/AGENTS.md`](../fy26/AGENTS.md).

The skills also work without picking an agent: type `/` in chat (for example `/fy26-troubleshooting`), or just ask, and Copilot loads the matching skill.

**Handoff buttons** (`handoffs:` in each agent file) appear when the chat session runs in VS Code's Local harness. In Copilot sessions they do not; students pick the named agent from the Agent dropdown instead.

**Opened only the `fy26/` folder?** VS Code then looks for agents in `fy26/` only. [`fy26/.vscode/settings.json`](../fy26/.vscode/settings.json) turns on `chat.useCustomizationsInParentRepositories` so the agents and skills here are found; trust the parent folder when VS Code asks. If they still do not appear, enable that setting in your User settings, or open the repository root instead.

## Custom Instructions

**File:** `copilot-instructions.md`

These instructions are **always applied** to every Copilot interaction. They define:
- Python coding standards (type hints, PEP 8)
- Azure Functions patterns (v2 model)
- MCP conventions
- Teaching context for graduate students

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
| `azure-functions` | FY25 (archived): Azure Functions |
| `mcp-server` | FY25 (archived): MCP on Azure Functions |
| `python-testing` | FY25 (archived): pytest for Azure Functions |
| `agentic-ai` | FY25 (archived): agents with tool calling |
| `notebook-development` | Instructors: creating teaching lab notebooks |

### Enable Skills

1. Open VS Code Settings (`Cmd+,`)
2. Search: `chat.useAgentSkills`
3. Enable the checkbox

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
- "Create a new lab notebook" → Should use `notebook-development` skill

Then pick **FY26 Guide** in the agent dropdown and say "I am lost": it should check your setup and offer handoff buttons.

## Resources

- [Custom agents in VS Code](https://code.visualstudio.com/docs/agent-customization/custom-agents)
- [Agent Skills in VS Code](https://code.visualstudio.com/docs/agent-customization/agent-skills)
- [Customizations in a monorepo (parent repository discovery)](https://code.visualstudio.com/docs/agent-customization/overview#_use-customizations-in-a-monorepo)
- [Agent Skills Docs](https://code.visualstudio.com/docs/copilot/copilot-customization)
- [Custom Instructions](https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot)
- [Agent Skills Standard](https://agentskills.io)
