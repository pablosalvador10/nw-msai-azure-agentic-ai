# Week 6 · RAG Apps + Tool Calling

**Date:** Nov 3 · **Notes:** [lecture.md](lecture.md) · **Lecture page:** [lecture.html](docs/lecture.html) · **Slides:** [slides.html](docs/slides.html) · **Lab:** [lab.ipynb](lab.ipynb) · **Submit:** one URL, before the Week 7 session

[← Week 5](../week05-fundamentals-of-azure-ai/README.md) · [FY26 home](../README.md) · [Next: Week 7 →](../week07-multi-agent-systems/README.md)

| In this folder | What it is |
|---|---|
| `README.md` | Start here: goals, preparation, the exercise and how it is graded |
| [`lecture.md`](lecture.md) | The lecture notes: the content of the session |
| [`lab.ipynb`](lab.ipynb) | Required: the lab you run in class; it ships the service you submit |
| [`deep-dive.ipynb`](deep-dive.ipynb) | Optional, not graded, for after you submit: the notes in more depth, with code |
| [`docs/lecture.html`](docs/lecture.html) | The notes as one page with a contents column; prints to PDF |
| [`docs/slides.html`](docs/slides.html) | The notes as slides for the session |

## Why this week matters

A model knows what it read during training, which does not include your company's handbook, today's prices or the bikes at a station right now. Two techniques close that gap. **Retrieval-augmented generation (RAG)** finds the right passages and puts them in front of the model. **Tool calling** lets the model ask your code for facts and actions: compute a fare, read live data. Together they turn a well-spoken model into one that is right, and can show why.

## By the end you can

- Explain embeddings and cosine similarity, and build retrieval from scratch.
- Ground an answer in retrieved passages and return **citations**.
- Make the model say "I don't know" when the sources are silent (**abstention**).
- Write the **tool-calling loop** by hand: tool schema, function call, result, final answer.
- Design tools a model uses well: clear names, "when to use" descriptions, constrained arguments, errors as data.
- Build the same thing with **Microsoft Agent Framework**, and know what it does for you.

## Before class (about 1 hour)

1. Your Week 5 service is deployed and scores in the harness.
2. Read the Learn module [Develop generative AI apps that use tools](https://learn.microsoft.com/en-us/training/modules/use-generative-ai-tools/).
3. Skim the handbook your service will answer from: [`app/data/handbook/`](../app/data/handbook/). Ten short pages.

## Lecture notes

The content of the session is in **[lecture.md](lecture.md)**: embeddings and similarity, the RAG pipeline, chunking, hybrid retrieval and reranking, grounding with citations and abstention, evaluating RAG, managed RAG on Azure (**Azure AI Search, Foundry IQ** and agentic retrieval, file search), the tool-calling protocol, tool design, tools across the stack, and one agent with **Microsoft Agent Framework**. The lab follows the same order.

## The exercise

**Service:** `POST /v1/ask` answers a rider's question with `answer`, `citations` (handbook `doc_id`s), `tool_calls`, and `abstained` ([contract](../app/contract.py)).

**Starting point:** [`app/services/ask.py`](../app/services/ask.py) does classic retrieve-then-generate: one search, one model call. It has no tools, so it guesses at prices and cannot see stations.

**Your job:** replace it with an agent that has three tools (`search_handbook`, `quote_fare`, `get_station`, already in [`app/tools.py`](../app/tools.py)) and returns structured output. Then tune instructions and retrieval: 100 on the public questions is reachable, and the lab (Part 6) lists the typical fixes. Write rules that generalize: we grade on questions you have not seen.

| Check | Weight | What it measures |
|---|---|---|
| `core.health`, `core.info` | 1 + 1 | The service is up and identifies you |
| `w06.ask.schema` | 1 | Every response matches the contract |
| `w06.ask.facts` | 3 | Answers contain the facts from the handbook |
| `w06.ask.citations` | 2 | Answers cite the right page (at most three citations) |
| `w06.ask.tools` | 2 | Prices and station data come from tools, with the right value |
| `w06.ask.abstain` | 1 | `abstained` is true exactly when the handbook has no answer |
| `w06.latency` | 1 | Median latency at or under 8 s, scaled by valid responses |

**Stuck?** In Copilot Chat, pick **Pablo · Fundamentals** and name the check, for example: "Week 6, `w06.ask.citations` is PART. What do the failing cases have in common? First hint only." It explains and hints; the code stays yours. **Arvind · Data** compares the pages your answers cite with the expected ones, **Will · Infra and deploy** helps you deploy, and before the deadline ask **Pablo · Scoring** "Am I ready to submit?". New to the agents? Read [Your course agents](../foundations/docs/agents.html).

## The deep dive (optional)

[`deep-dive.ipynb`](deep-dive.ipynb) is for after you submit. It is not graded, and it does not edit `app/` or deploy, so it cannot change your score. Its nine parts measure retrieval and try the alternatives: BM25, hybrid and multi-query search, chunk and embedding sizes, the edges of tool calling, and two ways to do RAG in Agent Framework ([list of parts](docs/lecture.html#deep-dive)). Same setup as the lab; run the parts in order. Cost: a few cents of embeddings and model calls.

## Go further in your service (optional)

Ideas beyond the exercise, mostly in your own service. If one changes `app/`, score it in-process before you deploy it.

- **Hybrid retrieval.** Add keyword matching next to the vectors: station ids and fee names are exact strings. Which questions improve?
- **Chunking.** Our chunks are handbook sections. Try smaller ones. What happens to citations?
- **Managed retrieval.** At scale you would not keep vectors in memory. Read how [Foundry IQ](https://learn.microsoft.com/en-us/azure/foundry/agents/concepts/what-is-foundry-iq) and [agentic retrieval in Azure AI Search](https://learn.microsoft.com/en-us/azure/search/agentic-retrieval-overview) do the job as a service: the model plans sub-queries, the service runs and merges them.
- **Tool design.** Rewrite a tool description badly on purpose and watch the score drop. Then read [Writing effective tools for agents](https://www.anthropic.com/engineering/writing-tools-for-agents).

## Microsoft Learn and further reading

| Topic | Resource |
|---|---|
| Tools in Foundry apps: functions, file search, web search | [Develop generative AI apps that use tools](https://learn.microsoft.com/en-us/training/modules/use-generative-ai-tools/) (module) |
| RAG, conceptually | [Introduction to retrieval-augmented generation concepts](https://learn.microsoft.com/en-us/training/modules/rag-fundamentals/) (module) |
| RAG for agents, managed | [Build knowledge-enhanced AI agents with Foundry IQ](https://learn.microsoft.com/en-us/training/modules/introduction-foundry-iq/) (module) |
| Agent Framework | [Microsoft Agent Framework overview](https://learn.microsoft.com/en-us/agent-framework/overview/agent-framework-overview) |
| The tool-calling protocol | [Function calling (OpenAI)](https://developers.openai.com/api/docs/guides/function-calling) |
| Embeddings, models and dimensions | [Vector embeddings (OpenAI)](https://developers.openai.com/api/docs/guides/embeddings) |
| Designing tools that models use well | [Writing effective tools for agents (Anthropic)](https://www.anthropic.com/engineering/writing-tools-for-agents) |
