"""Week 7: a multi-agent team resolves a support case.

This is the starting version: every specialist works on every case.

    case -> policy + billing + operations (in parallel) -> writer -> reply

- Specialists run concurrently (Agent Framework ConcurrentBuilder), each with its own tools.
- The writer turns their notes into one reply for the rider.

It works, but it is slow and wasteful, and specialists act on cases that are not
theirs. In the Week 7 lab you add a triage agent that picks the specialists.

Every tool call is recorded; credits and tickets become `actions` in the response.
"""

from agent_framework import Agent
from agent_framework.orchestrations import ConcurrentBuilder

from app.contract import Action, Citation, ResolveRequest, ResolveResponse
from app.guardrails import REFUSALS, is_content_filter_error, screen
from app.state import AppState
from app.tools import get_station, issue_credit, open_ticket, quote_fare, recording, search_handbook

SPECIALISTS: dict[str, tuple[str, list]] = {
    "policy": (
        "You are the policy specialist. Find the rules that apply with search_handbook and explain them "
        "in two or three sentences. Quote numbers exactly.",
        [search_handbook],
    ),
    "billing": (
        "You are the billing specialist. Find the policy with search_handbook, use quote_fare to compute "
        "amounts, and call issue_credit once if the policy says the rider is owed credit. Credit exactly "
        "what the policy says. State the amount and status.",
        [search_handbook, quote_fare, issue_credit],
    ),
    "operations": (
        "You are the operations specialist. Use get_station for availability. Call open_ticket once for "
        "each broken bike (bike_repair) or broken dock or station (station_repair). State what you did.",
        [get_station, open_ticket, search_handbook],
    ),
}

WRITER = """You write the final reply to the rider for Lakeshore Ride Support.
Use only the specialists' notes. Say what was done (credits, tickets) and what the rider should do next.
Under 120 words. Plain, friendly, no internal jargon."""


async def resolve(state: AppState, request: ResolveRequest) -> ResolveResponse:
    """Week 7: resolve a support case with a team of agents: actions, route and a reply."""
    if guardrail := screen(request.case):
        return ResolveResponse(id=request.id, resolution=REFUSALS[guardrail], route=["guardrail"], guardrail=guardrail)
    if state.offline:
        return ResolveResponse(id=request.id, resolution="(offline mode) Case received.", route=["policy"])

    client = state.models.agent_client()
    chosen = list(SPECIALISTS)
    with recording(state) as calls:
        try:
            team = [
                Agent(client=client, name=name, instructions=SPECIALISTS[name][0], tools=SPECIALISTS[name][1])
                for name in chosen
            ]
            # ConcurrentBuilder fans out to two or more agents and gathers their answers.
            workflow = ConcurrentBuilder(participants=team).build()
            outcome = await workflow.run(request.case)
            notes = _notes(outcome.get_outputs())

            reply = await Agent(client=client, name="writer", instructions=WRITER).run(
                f"Case:\n{request.case}\n\nSpecialist notes:\n{notes}"
            )
        except Exception as exc:
            if is_content_filter_error(exc):
                return ResolveResponse(
                    id=request.id, resolution=REFUSALS["unsafe"], route=["guardrail"], guardrail="unsafe"
                )
            raise

    actions = [
        Action(name=c["name"], arguments=c["arguments"], status=str(c["result"].get("status", "unknown")))
        for c in calls
        if c["name"] in ("issue_credit", "open_ticket")
    ]
    cited = [hit["doc_id"] for c in calls if c["name"] == "search_handbook" for hit in c["result"][:1]]
    return ResolveResponse(
        id=request.id,
        resolution=reply.text,
        route=[*chosen, "writer"],
        actions=actions,
        citations=[Citation(doc_id=d) for d in dict.fromkeys(cited)],
    )


def _notes(outputs: list) -> str:
    lines = [
        f"[{message.author_name or 'specialist'}] {message.text}"
        for output in outputs
        for message in getattr(output, "messages", []) or []
        if message.role == "assistant" and message.text
    ]
    return "\n".join(lines) or "\n".join(str(o) for o in outputs)
