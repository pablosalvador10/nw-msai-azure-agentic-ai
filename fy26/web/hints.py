"""What to try when a check is not at 100%. Hints point at the cause and the file; they never give answers.

The harness data on the website is the public data. Your grade uses hidden cases of the same kind,
so a fix that only works for the listed ids will not carry over.
"""

from typing import Any

WEEK_DIRS = {
    5: "week05-fundamentals-of-azure-ai",
    6: "week06-rag-and-tool-calling",
    7: "week07-multi-agent-systems",
    8: "week08-harnesses-and-agentic-coding",
    10: "week10-production-agentic-systems",
}

WEEK_TITLES = {
    5: "Fundamentals of Azure AI",
    6: "RAG and tool calling",
    7: "Multi-agent systems",
    8: "Harnesses and agentic coding",
    10: "Production agentic systems",
}

# check id -> (what to try, files to open)
HINTS: dict[str, tuple[str, list[str]]] = {
    "core.health": (
        "GET /health did not answer. Paste the base URL from `terraform output app_url`, then check that the "
        "latest revision is running: `az containerapp revision list -n <app> -g <rg> -o table`.",
        ["infra/README.md"],
    ),
    "core.info": (
        "GET /v1/info must report your student_id, contract fy26.v1 and a list of capabilities. Set student_id in "
        "infra/terraform.tfvars and deploy again. Do not change the contract.",
        ["app/main.py", "app/contract.py"],
    ),
    "w05.chat": (
        "POST /v1/chat must return a non-empty answer and the name of the model deployment that produced it.",
        ["app/services/chat.py"],
    ),
    "w05.validation": (
        "Missing, mistyped, empty and malformed input must be rejected with 4xx before any model call. Let the "
        "request model from the contract validate the body; do not turn validation errors into 200 responses.",
        ["app/contract.py", "app/services/classify.py"],
    ),
    "w05.classify.schema": (
        "Every response must echo the id, use only the allowed category and urgency values, and keep the summary "
        "at 300 characters or less. Structured output stops the model from inventing values.",
        ["app/services/classify.py", "app/contract.py"],
    ),
    "w05.classify.category": (
        "Read the misses: which categories does the model confuse? Define each category in the instructions and "
        "add a few contrasting examples. Write rules that generalize: hidden tickets are different.",
        ["app/services/classify.py"],
    ),
    "w05.classify.urgency": (
        "State exactly what makes a ticket high, medium or low urgency (safety, money, a blocked ride) and show "
        "one contrasting example per boundary.",
        ["app/services/classify.py"],
    ),
    "w05.latency": (
        "Median triage latency should be 4 s or less. Lower the reasoning effort, shorten the prompt and reuse "
        "one client. Invalid responses also lower this score.",
        ["app/models.py", "app/services/classify.py"],
    ),
    "w06.ask.schema": (
        "Every answer needs id, answer, citations (each with doc_id), tool_calls and abstained, as in the contract.",
        ["app/services/ask.py", "app/contract.py"],
    ),
    "w06.ask.facts": (
        "Answers must state the handbook's facts: numbers, times and conditions. Retrieve with search_handbook "
        "and instruct the agent to answer from the retrieved text only.",
        ["app/services/ask.py", "app/rag.py"],
    ),
    "w06.ask.citations": (
        "Cite the handbook page the answer relies on (doc_id), at most three. Cite what you used, not every "
        "search result, and cite a page even when a tool supplied the number.",
        ["app/services/ask.py"],
    ),
    "w06.ask.tools": (
        "Prices and station availability must come from quote_fare and get_station with the right arguments, "
        "and the answer must report the tool's value. The model never computes a fare.",
        ["app/services/ask.py", "app/tools.py"],
    ),
    "w06.ask.abstain": (
        "Set abstained to true only when the handbook has no answer, and false for every answered question.",
        ["app/services/ask.py"],
    ),
    "w06.latency": (
        "Median answer latency should be 8 s or less: fewer tool round trips, lower reasoning effort, a smaller "
        "retrieved context.",
        ["app/services/ask.py", "app/models.py"],
    ),
    "w07.resolve.schema": (
        "Every resolution needs id, a non-empty resolution, route (a list) and actions with name, arguments and "
        "status.",
        ["app/services/resolve.py", "app/contract.py"],
    ),
    "w07.resolve.route": (
        "Send each case only to the specialists it needs. A triage step with structured output beats calling "
        "everyone: each extra specialist costs points.",
        ["app/services/resolve.py"],
    ),
    "w07.resolve.actions": (
        "Credits and tickets need exact arguments. Amounts come from app/domain.py through tools, and a credit is "
        "issued only when the policy says one is owed.",
        ["app/services/resolve.py", "app/domain.py", "app/tools.py"],
    ),
    "w07.resolve.answer": (
        "The final reply must state the key facts from the specialists' results: amounts, what happens next.",
        ["app/services/resolve.py"],
    ),
    "w07.latency": (
        "Median resolution latency should be 20 s or less: run independent specialists concurrently and skip the "
        "ones a case does not need.",
        ["app/services/resolve.py"],
    ),
    "w08.mcp.discover": (
        "POST /mcp server/discover must answer with protocol 2026-07-28 and a server name. A 421 means the Host "
        "check rejected your URL: PUBLIC_HOSTNAME must match it.",
        ["app/mcp_server.py", "app/main.py"],
    ),
    "w08.mcp.tools": (
        "tools/list must publish search_handbook, quote_fare and get_station, each with an input schema.",
        ["app/mcp_server.py"],
    ),
    "w08.mcp.call": (
        "Tools called over MCP must return the same data as the Python functions behind them.",
        ["app/mcp_server.py", "app/tools.py"],
    ),
    "w08.mcp.new_tool": (
        "Build nearest_station_with_docks in app/domain.py, publish it in app/mcp_server.py, and make "
        "tests/test_week08_nearest_station.py pass before you deploy.",
        ["app/domain.py", "app/mcp_server.py", "tests/test_week08_nearest_station.py"],
    ),
    "w10.injection": (
        "Instructions hidden in user input must not change behavior or leak secrets. Screen the input and set "
        'guardrail to "prompt_injection" when you refuse.',
        ["app/guardrails.py", "app/services/ask.py"],
    ),
    "w10.unsafe": (
        'Refuse harmful requests: set guardrail to "unsafe" (or abstained to true) instead of answering.',
        ["app/guardrails.py", "app/services/ask.py"],
    ),
    "w10.limits": (
        "Reject bodies over the size limit with 413 or 422, and malformed JSON with 4xx.",
        ["app/middleware.py"],
    ),
    "w10.burst": (
        "20 concurrent requests must return 2xx or 429, never 5xx: limit or queue instead of failing, and retry "
        "model 429s with backoff.",
        ["app/middleware.py", "app/models.py"],
    ),
    "w10.request_id": (
        "Echo X-Request-ID when the client sends one, and generate one when it does not.",
        ["app/middleware.py"],
    ),
    "w10.ready": ("GET /ready must return 200 when the service can serve traffic.", ["app/main.py"]),
    "w10.auth": (
        "Turn on the API key (course.set_api_key()), deploy, and paste the key in the API key field above. "
        "Without the key, /v1 routes must answer 401.",
        ["app/middleware.py", "week10-production-agentic-systems/README.md"],
    ),
    "w10.regression": (
        "Week 10 changes must not break Week 6 answers. Score Week 6 again and loosen any screen that blocks "
        "legitimate questions.",
        ["app/guardrails.py", "app/services/ask.py"],
    ),
}


def week_links(week: int) -> list[dict[str, str]]:
    folder = WEEK_DIRS[week]
    return [
        {"label": "Weekly overview", "href": f"/{folder}/README.md"},
        {"label": "Lecture", "href": f"/{folder}/docs/lecture.html"},
        {"label": "Main lab", "href": f"/{folder}/lab.ipynb"},
    ]


def advice(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Hint and file links per check id of a report. Kept apart from the report so the proof stays unchanged."""
    result = {}
    for check in report.get("checks", []):
        hint, files = HINTS.get(check.get("id", ""), ("", []))
        result[check.get("id", "")] = {"hint": hint, "files": [{"label": f, "href": f"/{f}"} for f in files]}
    return result
