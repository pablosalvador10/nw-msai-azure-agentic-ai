"""Week 8 specification, written as tests.

These tests are skipped until `app.domain.nearest_station_with_docks` exists.
Build it with your coding agent; when the function appears, the tests run.

Spec: given a station id, return the closest *other* station that is open and
has at least one free dock, by great-circle (haversine) distance:
    {"station_id": "LS-08", "name": "Arts Campus", "distance_km": 0.47, "docks_available": 6}
Unknown station ids return {"error": "..."}. Publish it as an MCP tool with the same name.
"""

import pytest

from app import domain

nearest = getattr(domain, "nearest_station_with_docks", None)
pytestmark = pytest.mark.skipif(nearest is None, reason="Week 8: implement app.domain.nearest_station_with_docks")


def test_skips_itself_and_full_stations():
    assert nearest("LS-03")["station_id"] == "LS-08"  # LS-14 is closer but full


def test_uses_great_circle_distance():
    assert nearest("LS-16")["station_id"] == "LS-06"  # flat lat/lon distance would pick LS-05


def test_returns_the_contract_fields():
    result = nearest("LS-12")
    assert {"station_id", "name", "distance_km", "docks_available"} <= result.keys()
    assert result["docks_available"] > 0


def test_unknown_station_is_an_error():
    assert "error" in nearest("LS-99")


def test_published_over_mcp(client):
    from harness.checks.week08 import call_tool
    from harness.client import Target
    from harness.engine import Context

    ctx = Context(target=Target(client=client), week=8)
    assert call_tool(ctx, "nearest_station_with_docks", {"station_id": "LS-03"})["station_id"] == "LS-08"
