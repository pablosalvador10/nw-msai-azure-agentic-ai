"""The harness datasets must agree with the domain code and the handbook."""

import json
from pathlib import Path

import pytest

from app import domain
from app.rag import doc_ids

DATA = Path(__file__).parents[1] / "harness" / "data"


def rows(name: str) -> list[dict]:
    return [json.loads(line) for line in (DATA / f"{name}.jsonl").read_text().splitlines() if line.strip()]


@pytest.mark.parametrize("name", ["week05", "week06", "week07", "week08", "week10"])
def test_ids_are_unique(name):
    ids = [r["id"] for r in rows(name)]
    assert len(ids) == len(set(ids))


def test_week06_gold_matches_domain():
    for row in rows("week06"):
        for doc in row.get("doc_ids", []):
            assert doc in doc_ids(), row["id"]
        tool = row.get("tool")
        if tool and tool["name"] == "quote_fare":
            assert domain.quote_fare(**tool["arguments"])["total"] == row["value"], row["id"]
        if tool and tool["name"] == "get_station" and "value" in row:
            assert domain.get_station(tool["arguments"]["station_id"])["ebikes_available"] == row["value"], row["id"]


def test_week07_credit_amounts_follow_policy():
    expected = {
        "c01": domain.quote_fare("member", 40, True)["total"],
        "c02": 3.00 - domain.quote_fare("student", 70, False)["total"],
        "c03": round(25 * 0.20, 2),
        "c04": 1200 - 150,
    }
    for row in rows("week07"):
        for action in row["actions"]:
            if action["name"] == "issue_credit":
                assert action["arguments"]["amount"] == pytest.approx(expected[row["id"]]), row["id"]
                status = domain.issue_credit("R", action["arguments"]["amount"], "")["status"]
                assert action["status"] == status, row["id"]


def test_week08_nearest_station_gold():
    def nearest(station_id: str) -> str:
        origin = domain.get_station(station_id)
        candidates = [
            s
            for s in domain.list_stations()
            if s["id"] != origin["id"] and s["status"] == "open" and s["docks_available"] > 0
        ]
        return min(candidates, key=lambda s: domain.distance_km(origin, s))["id"]

    for row in rows("week08"):
        if row["tool"] == "nearest_station_with_docks":
            assert nearest(row["arguments"]["station_id"]) == row["expect"]["station_id"], row["id"]
        if row["tool"] == "quote_fare":
            got = domain.quote_fare(**row["arguments"])
            assert all(got[k] == v for k, v in row["expect"].items()), row["id"]
