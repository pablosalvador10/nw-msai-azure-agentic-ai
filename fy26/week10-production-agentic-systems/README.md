# Week 10 · Production Agentic Systems

**Date:** Dec 1 · **Notes:** [lecture.md](lecture.md) · **Lecture page:** [lecture.html](docs/lecture.html) · **Slides:** [slides.html](docs/slides.html) · **Lab:** [lab.ipynb](lab.ipynb) · **Submit:** one URL and your API key, by the final deadline

[← Week 8](../week08-harnesses-and-agentic-coding/README.md) · [FY26 home](../README.md)

| In this folder | What it is |
|---|---|
| `README.md` | Start here: goals, preparation, the exercise and how it is graded |
| [`lecture.md`](lecture.md) | The lecture notes: the content of the session |
| [`lab.ipynb`](lab.ipynb) | Required: the lab you run in class; it ships the service you submit |
| [`deep-dive.ipynb`](deep-dive.ipynb) | Optional, not graded, for after you submit: the notes in more depth, with code |
| [`docs/lecture.html`](docs/lecture.html) | The notes as one page with a contents column; prints to PDF |
| [`docs/slides.html`](docs/slides.html) | The notes as slides for the session |

## Why this week matters

A demo has one user who wants it to work. Production has thousands of users, some of whom want it to fail: they will paste instructions into a question, ask for things you must refuse, send a megabyte of text, or call you two hundred times a minute. You cannot prove a model-based system is safe. You can **layer** defenses, **observe** what happens, **evaluate** quality continuously, and **measure** that each change did not break what worked. This week turns your service into something you would put your name on.

## By the end you can

- Threat-model an LLM application with the OWASP Top 10 for LLM applications, including indirect prompt injection.
- Layer guardrails: platform guardrails and Prompt Shields, input screening, output checks, least-privilege tools.
- Measure the false-positive cost of every guardrail.
- Enforce limits and authentication at the edge: body size, rate limits, request ids, API key; and explain how MCP authorization works.
- Read traces and metrics in Application Insights with KQL, without recording personal data.
- Evaluate answer quality with an LLM judge, built from scratch, calibrated against people, and know the managed alternative.

## Before class (about 1 hour)

1. Your Week 8 service is deployed and scores in the harness.
2. Read [LLM01:2025 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/) and skim the rest of the [OWASP Top 10 for LLM applications](https://genai.owasp.org/llm-top-10/).
3. Skim the learning path [Operationalize generative AI applications (GenAIOps)](https://learn.microsoft.com/en-us/training/paths/operationalize-gen-ai-apps/).

## Lecture notes

The content of the session is in **[lecture.md](lecture.md)**: threat modeling and the lethal trifecta, the OWASP Top 10 for LLM and agentic applications, prompt injection and the architectural patterns that resist it, **Foundry guardrails** (risks, intervention points including tool calls, Prompt Shields), your own guardrails and their false positives, identity and **Entra agent identities**, edge limits and the **AI gateway**, reliability and safe rollout, OpenTelemetry and KQL, evaluation and calibrated judges, the **AI Red Teaming Agent**, GenAIOps, fleet governance with the **Foundry control plane**, cost engineering, and a production readiness checklist. The lab follows the same order.

## The exercise

**Service:** all routes, hardened. `/v1/ask` and `/v1/resolve` set `guardrail` to `"prompt_injection"` or `"unsafe"` when they refuse ([contract](../app/contract.py)). `/v1/*` and `/mcp` require an `X-API-Key` header.

**Starting point:** [`app/guardrails.py`](../app/guardrails.py) screens input with a few regular expressions; [`app/middleware.py`](../app/middleware.py) already adds request ids, a body limit and a rate limit; the API key is off.

**Your job:** contain injection attempts and refuse harmful requests without refusing legitimate riders, turn the API key on, and prove nothing earlier broke. Once the key is on, every check can reach 100 locally; the injection check lists any attempt that was contained but not labelled `prompt_injection`.

| Check | Weight | What it measures |
|---|---|---|
| `core.health`, `core.info` | 1 + 1 | The service is up and identifies you |
| `w10.injection` | 3 | Injection attempts do not take over the answer (full marks if flagged `prompt_injection`) |
| `w10.unsafe` | 1 | Harmful requests are refused |
| `w10.limits` | 2 | Oversized and malformed input gets a 4xx, never a 5xx |
| `w10.burst` | 2 | 20 concurrent requests, no 5xx or timeout (429 is fine) |
| `w10.request_id` | 1 | `X-Request-ID` is echoed, or generated when missing |
| `w10.ready` | 1 | `GET /ready` answers 200 |
| `w10.auth` | 1 | Requests without the API key get 401; with it, 200 |
| `w10.regression` | 2 | Week 6 answers are still right: guardrails did not block real questions |

Your final URL is also scored with the Week 5 to 8 harnesses, so a guardrail that breaks an earlier route costs points there too. Submit the URL and your API key (the value of `SERVICE_API_KEY` in `fy26/.env`) through the course site, never in a public place.

**Stuck?** In Copilot Chat, pick **Pablo · Fundamentals** and name the check, for example: "Week 10, `w10.injection` is PART. Which controls fired, and which cases got through? First hint only." It explains and hints; the code stays yours. **Arvind · Data** puts both guardrail error rates side by side and queries your telemetry, **Will · Infra and deploy** helps you deploy and turn on the API key, and before the deadline ask **Pablo · Scoring** "Am I ready to submit?". New to the agents? Read [Your course agents](../foundations/docs/agents.html).

## The deep dive (optional)

[`deep-dive.ipynb`](deep-dive.ipynb) is for after you submit. It is not graded, and it does not edit `app/` or deploy, so it cannot change your score. The lab adds one layer of each defense; the deep dive's seven parts measure them: input screens, attack success rate, indirect injection, rate limits, traces, KQL and judges ([list of parts](docs/lecture.html#deep-dive)). Same setup as the lab; run the parts in order. Part 6 reads the logs of your deployed service, so run the harness against your URL first. Cost: well under a dollar.

## Go further in your service (optional)

Ideas beyond the exercise, mostly in your own service. If one changes `app/`, score it in-process before you deploy it.

- Run the [AI Red Teaming Agent](https://learn.microsoft.com/en-us/azure/foundry/concepts/ai-red-teaming-agent) (built on PyRIT) against your service and compare attack success rates before and after your guardrails.
- Replace the regular expressions with a model-based screen and compare: what does it catch, what does it cost in latency and tokens?
- Add an **output** guardrail: a canary string in the instructions that must never appear in an answer.
- Write a KQL alert query: p95 latency of `/v1/ask` above 10 s in the last 15 minutes.
- Protect `/mcp` with Entra ID tokens instead of the shared key ([MCP authorization in the Python SDK](https://py.sdk.modelcontextprotocol.io/run/authorization/)).
- Run [Foundry evaluations](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluate-agent) on your agent and compare them with your own judge.

## Microsoft Learn and further reading

| Topic | Resource |
|---|---|
| Evaluation, monitoring, tracing, CI for AI apps | [Operationalize generative AI applications (GenAIOps)](https://learn.microsoft.com/en-us/training/paths/operationalize-gen-ai-apps/) (learning path) |
| Tracing with OpenTelemetry and Application Insights | [Analyze and debug your generative AI app with tracing](https://learn.microsoft.com/en-us/training/modules/tracing-generative-ai-app/) (module) |
| Harms, guardrails and content filters | [Implement a responsible generative AI solution in Microsoft Foundry](https://learn.microsoft.com/en-us/training/modules/responsible-ai-studio/) (module) |
| Guardrails, controls and Prompt Shields | [Guardrails and controls in Microsoft Foundry](https://learn.microsoft.com/en-us/azure/foundry/guardrails/guardrails-overview) · [Prompt Shields](https://learn.microsoft.com/en-us/azure/ai-services/content-safety/concepts/jailbreak-detection) |
| Evaluating agents in Foundry | [Evaluate your agent](https://learn.microsoft.com/en-us/azure/foundry/observability/how-to/evaluate-agent) · [Agent evaluators](https://learn.microsoft.com/en-us/azure/foundry/concepts/evaluation-evaluators/agent-evaluators) |
| Threats specific to LLM apps | [OWASP Top 10 for LLM applications](https://genai.owasp.org/llm-top-10/) |
| Containment before steering | [How we contain Claude (Anthropic)](https://www.anthropic.com/research/how-we-contain-claude) |
| Securing an MCP server | [MCP security best practices](https://modelcontextprotocol.io/specification/2026-07-28/basic/security_best_practices) |
| Health probes on Container Apps | [Health probes in Azure Container Apps](https://learn.microsoft.com/en-us/azure/container-apps/health-probes) |
