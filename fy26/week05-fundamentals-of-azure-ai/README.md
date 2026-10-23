# Week 5 · Fundamentals of Azure AI

**Date:** Oct 27 · **Instructors:** Pablo, Arvind · **Notes:** [lecture.md](lecture.md) · **Lecture page:** [lecture.html](docs/lecture.html) · **Slides:** [slides.html](docs/slides.html) · **Lab:** [lab.ipynb](lab.ipynb) · **Submit:** one URL, before the Week 6 session

[FY26 home](../README.md) · [Next: Week 6 →](../week06-rag-and-tool-calling/README.md)

| In this folder | What it is |
|---|---|
| `README.md` | Start here: goals, preparation, the exercise and how it is graded |
| [`lecture.md`](lecture.md) | The lecture notes: the content of the session |
| [`lab.ipynb`](lab.ipynb) | Required: the lab you run in class; it ships the service you submit |
| [`deep-dive.ipynb`](deep-dive.ipynb) | Optional, not graded, for after you submit: the notes in more depth, with code |
| [`docs/lecture.html`](docs/lecture.html) | The notes as one page with a contents column; prints to PDF |
| [`docs/slides.html`](docs/slides.html) | The notes as slides for the session |

## Why this week matters

Every AI feature you will build sits on one primitive: send text to a model, get text (or JSON) back. This week you learn that primitive properly: where models live in Azure, how you authenticate without keys, what you pay for, and how to make a model return data your code can trust. Then you put it behind an API and measure it.

## By the end you can

- Explain the Microsoft Foundry resource model: account, project, deployment, endpoint.
- Call a model with the Responses API using Entra ID, and read its token usage.
- Choose reasoning effort, use prompt caching, keep conversation state, and stream output.
- Get **structured output** that always matches a schema, and validate it.
- Improve a prompt by measurement, not by impression, using the harness.

## Before class (about 1 hour; add 30 minutes if FastAPI or identity are new to you)

1. Finish [Setup](../setup/README.md). You should have a URL that scores in the harness.
2. Read the Learn module [Develop a generative AI chat app with Microsoft Foundry](https://learn.microsoft.com/en-us/training/modules/foundry-sdk/).
3. If FastAPI or identity are new to you, do the primers: [FastAPI](../foundations/fastapi.ipynb), [Identity and access](../foundations/identity.ipynb).

## Lecture notes

The content of the session is in **[lecture.md](lecture.md)**: the Azure AI stack and Microsoft Foundry's resource model, choosing models and deployment types, quota and throttling, keyless identity and RBAC, the Responses API, tokens and cost, structured output, prompts improved by measurement, and **Foundry Agent Service** (prompt, hosted and ephemeral agents, conversations, tools and toolboxes). The lab follows the same order.

## The exercise

**Service:** `POST /v1/classify` triages a rider's message into a category, an urgency and a summary ([contract](../app/contract.py)). `POST /v1/chat` answers free text.

**Starting point:** [`app/services/classify.py`](../app/services/classify.py) only tells the model the category names. It scores in the 80s.

**Your job:** write instructions that define each category and the urgency rules, measure, iterate, deploy. 100 on the public data is reachable: every miss in the report points to a rule you can write. Write rules that generalize, never answers: we grade on tickets you have not seen. Deploy as soon as you beat the baseline, then keep improving and redeploy: a deployed improvement counts, an undeployed one does not.

| Check | Weight | What it measures |
|---|---|---|
| `core.health`, `core.info` | 1 + 1 | The service is up and identifies you |
| `w05.chat` | 1 | `/v1/chat` answers and names its model |
| `w05.validation` | 1 | Bad input gets a 4xx, not a 500 |
| `w05.classify.schema` | 1 | Every response matches the contract |
| `w05.classify.category` | 3 | Category accuracy |
| `w05.classify.urgency` | 2 | Urgency accuracy |
| `w05.latency` | 1 | Median latency at or under 4 s, scaled by valid responses |

**Stuck?** In Copilot Chat, pick **FY26 Lab Tutor** and name the check, for example: "Week 5, `w05.classify.urgency` is PART. What do the failing tickets have in common? First hint only." It explains and hints; the code stays yours. **FY26 Deploy Doctor** helps you ship, **FY26 Submit Check** checks you before the deadline. New to the agents? Read [Your course agents](../foundations/docs/agents.html).

## The deep dive (optional)

[`deep-dive.ipynb`](deep-dive.ipynb) is for after you submit. It is not graded, and it does not edit `app/` or deploy, so it cannot change your score. Its eight parts take sections 2 to 11 of the notes further, with code you run on your own Foundry resource ([list of parts](docs/lecture.html#deep-dive)). Same setup as the lab; run the parts in order. Cost: a few cents of model calls.

## Go further in your service (optional)

Ideas beyond the exercise, mostly in your own service. If one changes `app/`, score it in-process before you deploy it.

- Add three or four **few-shot examples** to the instructions. Which tickets do they fix, which do they break?
- Try `reasoning={"effort": "low"}` in [`app/models.py`](../app/models.py) (the default for `gpt-5.4-mini` is `none`). Does accuracy move? Latency?
- Deploy `gpt-5.4-nano` next to `gpt-5.4-mini` (a second `azurerm_cognitive_deployment`) and compare accuracy, latency and price. Or try the [model router](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-router).
- Call a Claude model in Foundry with the same Entra ID token, through Anthropic's Messages API: [Claude in Microsoft Foundry](https://platform.claude.com/docs/en/build-with-claude/claude-in-microsoft-foundry).
- Make `summary` better: shorter, no personal data. How would you measure "better"?

## Microsoft Learn

| Topic | Resource |
|---|---|
| Foundry projects, endpoints and SDKs, Responses API | [Develop a generative AI chat app with Microsoft Foundry](https://learn.microsoft.com/en-us/training/modules/foundry-sdk/) (module) |
| The whole track, if you want more | [Develop generative AI apps on Microsoft Foundry](https://learn.microsoft.com/en-us/training/paths/develop-generative-ai-apps/) (learning path) |
| Quickstart in code | [Get started with Microsoft Foundry (code)](https://learn.microsoft.com/en-us/azure/foundry/quickstarts/get-started-code) |
| The v1 API and keyless auth | [API version lifecycle](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle) |
| Who may call what | [Role-based access control for Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/concepts/rbac-foundry) |
| Prompting the model you use | [Prompting GPT-5.4 models (OpenAI)](https://developers.openai.com/api/docs/guides/latest-model/gpt-5.4) · [Reasoning models (OpenAI)](https://developers.openai.com/api/docs/guides/reasoning) |
| What the model sees, and why less is more | [Effective context engineering for AI agents (Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) |
| Paying less for repeated prefixes | [Prompt caching (OpenAI)](https://developers.openai.com/api/docs/guides/prompt-caching) |
