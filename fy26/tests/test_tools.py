"""Agent tools: each returns JSON for the model and records the call for the API response."""

import asyncio
import json

import pytest

from app import domain, tools
from app.state import AppState
from tests.conftest import offline_settings


def test_tools_return_json_and_record_every_call() -> None:
    with tools.recording(AppState(offline_settings())) as calls:
        fare = json.loads(tools.quote_fare.func("member", 50, ebike=True))
        station = json.loads(tools.get_station.func("LS-07"))
        credit = json.loads(tools.issue_credit.func("R-1042", 5, "Dock did not lock"))
        ticket = json.loads(tools.open_ticket.func("bike_repair", "LS-14", "Flat tire on dock 3."))

    assert fare == domain.quote_fare("member", 50, True)
    assert station == domain.get_station("LS-07")
    assert [c["name"] for c in calls] == ["quote_fare", "get_station", "issue_credit", "open_ticket"]
    assert calls[0]["arguments"] == {"plan": "member", "minutes": 50, "ebike": True}
    assert calls[2]["result"] == credit
    assert calls[3]["result"] == ticket


def test_a_tool_outside_recording_still_answers() -> None:
    assert json.loads(tools.quote_fare.func("single", 10)) == domain.quote_fare("single", 10)


def test_search_handbook_needs_the_recording_context() -> None:
    with pytest.raises(RuntimeError, match="recording"):
        asyncio.run(tools.search_handbook.func("late fee"))


def test_search_handbook_returns_passages_with_their_doc_id() -> None:
    async def search() -> tuple[list[dict], list[dict]]:
        state = AppState(offline_settings())
        try:
            with tools.recording(state) as calls:
                hits = json.loads(await tools.search_handbook.func("How much does an e-bike cost?"))
        finally:
            await state.aclose()
        return hits, calls

    hits, calls = asyncio.run(search())

    assert hits
    assert all({"doc_id", "title", "section", "text", "score"} <= hit.keys() for hit in hits)
    assert calls == [
        {"name": "search_handbook", "arguments": {"query": "How much does an e-bike cost?"}, "result": hits}
    ]
