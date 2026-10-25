"""Run the real harness against the app in-process, and against a service that should fail.

Pinned expectations keep the harness honest: a do-nothing service must score low.
"""

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app import domain
from harness.checks.week08 import call_tool
from harness.client import Target
from harness.engine import Context, run_week


@pytest.mark.parametrize("week", [5, 6, 7, 8, 10])
def test_every_week_runs_offline(client, week):
    report = run_week(week, Target(client=client))
    data = report.to_dict()
    assert data["digest"].startswith("sha256:")
    assert data["service"]["student_id"] == "tester"
    assert report.results[0].id == "core.health" and report.results[0].passed
    assert all("crashed" not in r.detail for r in report.results), [r.detail for r in report.results]


def test_offline_baseline_scores(client):
    assert run_week(6, Target(client=client)).score >= 50
    week8 = run_week(8, Target(client=client))
    by_id = {r.id: r for r in week8.results}
    assert by_id["w08.mcp.discover"].passed
    assert by_id["w08.mcp.tools"].passed
    assert by_id["w08.mcp.call"].score >= 0.8  # offline embeddings are approximate
    if not hasattr(domain, "nearest_station_with_docks"):  # the Week 8 exercise is not built yet
        assert by_id["w08.mcp.new_tool"].score == 0.0


def test_mcp_tool_call_through_harness(client):
    ctx = Context(target=Target(client=client), week=8)
    assert call_tool(ctx, "quote_fare", {"plan": "member", "minutes": 50})["total"] == 0.75
    hits = call_tool(ctx, "search_handbook", {"query": "lost e-bike fee"})
    assert hits[0]["doc_id"] == "damage-and-lost-bikes"


def test_do_nothing_service_scores_low():
    """Health is fine, everything else returns a constant. This must not pass."""
    lazy = FastAPI()

    @lazy.get("/health")
    def health():
        return {"status": "ok"}

    @lazy.post("/{path:path}")
    def anything(path: str):
        return {"answer": "ok"}

    with TestClient(lazy) as c:
        for week in (5, 6, 7, 8):
            assert run_week(week, Target(client=c)).score < 25, week


def test_unreachable_service_is_reported_and_short_circuits():
    transport = httpx2.MockTransport(lambda request: httpx2.Response(503))
    target = Target(client=httpx2.Client(transport=transport, base_url="http://nowhere"), retries=0)
    report = run_week(5, target)
    assert report.score == 0
    assert all(r.detail.startswith("Skipped") for r in report.results[1:])
