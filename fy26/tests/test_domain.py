import pytest

from app import domain


@pytest.mark.parametrize(
    ("plan", "minutes", "ebike", "total"),
    [
        ("single", 30, False, 7.25),
        ("single", 20, True, 9.25),
        ("day_pass", 45, False, 0.00),
        ("day_pass", 60, False, 3.00),
        ("day_pass", 30, True, 7.50),
        ("member", 50, False, 0.75),
        ("member", 40, True, 7.20),
        ("student", 60, False, 0.00),
        ("student", 75, False, 2.25),
        ("single", 300, True, 50.00),
    ],
)
def test_quote_fare_follows_the_handbook(plan, minutes, ebike, total):
    assert domain.quote_fare(plan, minutes, ebike)["total"] == total


def test_quote_fare_rejects_unknown_plan():
    assert "error" in domain.quote_fare("platinum", 10)


def test_fare_cap_is_reported():
    assert domain.quote_fare("single", 300, True)["capped"] is True


def test_get_station_is_case_insensitive_and_reports_unknown_ids():
    assert domain.get_station("ls-05")["id"] == "LS-05"
    assert "error" in domain.get_station("LS-99")


def test_credit_above_limit_is_escalated():
    assert domain.issue_credit("R-1", 25.00, "x")["status"] == "issued"
    assert domain.issue_credit("R-1", 25.01, "x")["status"] == "escalated"
    assert domain.issue_credit("R-1", 0, "x")["status"] == "rejected"


def test_station_capacity_is_consistent():
    for s in domain.list_stations():
        if s["status"] == "open":
            assert s["classic_available"] + s["ebikes_available"] + s["docks_available"] == s["capacity"], s["id"]
