"""Tools the agents can call (Microsoft Agent Framework).

A tool is a Python function plus a description. The framework sends the
description and the parameter schema to the model; when the model asks for a
tool, the framework runs the function and sends the result back.

Every call is also recorded, so the API can report which tools ran
(`tool_calls` in /v1/ask, `actions` in /v1/resolve).
"""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Annotated, Any, Literal

from agent_framework import tool
from pydantic import Field

from app import domain
from app.state import AppState

_calls: ContextVar[list[dict[str, Any]] | None] = ContextVar("tool_calls", default=None)
_state: ContextVar[AppState | None] = ContextVar("app_state", default=None)


@contextmanager
def recording(state: AppState) -> Iterator[list[dict[str, Any]]]:
    """Collect every tool call made inside the `with` block."""
    calls: list[dict[str, Any]] = []
    calls_token, state_token = _calls.set(calls), _state.set(state)
    try:
        yield calls
    finally:
        _calls.reset(calls_token)
        _state.reset(state_token)


def _record(name: str, arguments: dict[str, Any], result: Any) -> str:
    calls = _calls.get()
    if calls is not None:
        calls.append({"name": name, "arguments": arguments, "result": result})
    return json.dumps(result)


async def handbook_search(state: AppState, query: str, top_k: int = 4) -> list[dict[str, Any]]:
    index = await state.index()
    hits = await index.search(state.models, query, top_k)
    return [
        {"doc_id": c.doc_id, "title": c.title, "section": c.heading, "text": c.text, "score": round(s, 3)}
        for c, s in hits
    ]


@tool
async def search_handbook(
    query: Annotated[str, Field(description="What to look up, in plain words.")],
) -> str:
    """Search the Lakeshore Ride handbook (prices, rules, policies). Returns passages with their doc_id."""
    state = _state.get()
    if state is None:
        raise RuntimeError("search_handbook must run inside tools.recording(state).")
    return _record("search_handbook", {"query": query}, await handbook_search(state, query))


@tool
def quote_fare(
    plan: Annotated[Literal["single", "day_pass", "member", "student"], Field(description="Rider's plan.")],
    minutes: Annotated[int, Field(description="Ride length in whole minutes.")],
    ebike: Annotated[bool, Field(description="True for an e-bike, false for a classic bike.")] = False,
) -> str:
    """Exact ride fee in US dollars for one ride. Always use this instead of computing prices."""
    args = {"plan": plan, "minutes": minutes, "ebike": ebike}
    return _record("quote_fare", args, domain.quote_fare(plan, minutes, ebike))


@tool
def get_station(
    station_id: Annotated[str, Field(description="Station id, for example LS-07.")],
) -> str:
    """Live classic bikes, e-bikes and free docks at one station."""
    return _record("get_station", {"station_id": station_id}, domain.get_station(station_id))


@tool
def issue_credit(
    rider_id: Annotated[str, Field(description="Rider id, for example R-1042.")],
    amount: Annotated[float, Field(description="Credit in US dollars.")],
    reason: Annotated[str, Field(description="Short reason, quoted from the policy.")],
) -> str:
    """Give a rider ride credit. Above $25 the case is escalated to a supervisor automatically."""
    args = {"rider_id": rider_id, "amount": amount, "reason": reason}
    return _record("issue_credit", args, domain.issue_credit(rider_id, amount, reason))


@tool
def open_ticket(
    category: Annotated[Literal["bike_repair", "station_repair", "rebalancing"], Field(description="Type of work.")],
    station_id: Annotated[str, Field(description="Station where the problem is, for example LS-14.")],
    summary: Annotated[str, Field(description="One sentence for the field team.")],
) -> str:
    """Open a maintenance ticket for the operations team."""
    args = {"category": category, "station_id": station_id, "summary": summary}
    return _record("open_ticket", args, domain.open_ticket(category, station_id, summary))
