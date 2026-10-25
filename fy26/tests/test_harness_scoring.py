import pytest

from harness.checks import week07
from harness.client import Exchange
from harness.engine import Context
from harness.scoring import arguments_match, fact_score, has_number, latency_score, normalize


def test_normalize():
    assert normalize("7 a.m. to 10 p.m.") == "7amto10pm"
    assert normalize("$2,500") == "$2500"
    assert normalize("$0.75") == "$0.75"


def test_fact_score_partial_credit():
    facts = [["$16", "16 dollars"], ["24 hours"]]
    assert fact_score("A Day Pass is $16 and lasts 24 hours.", facts) == 1.0
    assert fact_score("A Day Pass is $16.", facts) == 0.5


@pytest.mark.parametrize(
    ("answer", "facts", "expected"),
    [
        ("It costs $160 and lasts 24 hours.", [["$16", "16 dollars"], ["24 hours"]], 0.5),
        ("Riders must be 160 years old.", [["16"]], 0.0),
        ("It lasts 124 hours.", [["24 hours"]], 0.0),
        ("The fee is $16.50.", [["$16"]], 0.0),
        ("The fee is $16.00.", [["$16"]], 1.0),
        ("Fees are waived. 16 is the minimum age.", [["16"]], 1.0),
        ("The rate is 1.55 per minute.", [["1.5"]], 0.0),
        ("The rate is 1.50 per minute.", [["1.5"]], 1.0),
        ("It reopens on Dec 15.", [["dec 1"]], 0.0),
        ("A supervisor handles the escalation.", [["escalat"]], 1.0),
        # A sentence break or a space between two numbers must not hide a correct one.
        ("A Day Pass costs $16. 24 hours of use are included.", [["$16", "16 dollars"], ["24 hours"]], 1.0),
        ("A Day Pass costs $16. 5 riders can share one account.", [["$16"]], 1.0),
        ("See section 2. 16 is the minimum age.", [["16"]], 1.0),
        ("The pass lasts 24hours.", [["24 hours"]], 1.0),
        ("Open 7 a.m. to 10 p.m. daily.", [["7am"], ["10 pm"]], 1.0),
        ("Riders must be 1 6 years old.", [["16"]], 0.0),
    ],
)
def test_fact_score_matches_whole_numbers(answer, facts, expected):
    assert fact_score(answer, facts) == expected


def test_week07_actions_give_no_points_for_crediting_more_than_owed():
    owed = {"name": "issue_credit", "arguments": {"rider_id": "R-1", "amount": 5}, "status": "issued"}
    ticket = {"name": "open_ticket", "arguments": {"station_id": "LS-07"}, "status": "open"}
    row = {"id": "c1", "case": "Dock did not lock.", "specialists": ["billing"], "actions": [owed, ticket]}

    def score(actions: list[dict]) -> float:
        reply = Exchange("POST", "/v1/resolve", 200, 1.0, response={"id": "c1", "actions": actions})
        return week07.actions(Context(target=None, week=7, cache={"week07": [row], "w07": {"c1": reply}}))[0]

    assert score([owed, ticket]) == 1.0
    assert score([owed]) == 0.5
    assert score([owed, owed, ticket]) == 0.0
    assert score([owed, {**owed, "arguments": {"rider_id": "R-1", "amount": 50}}, ticket]) == 0.0
    # A rejected attempt moved no money, so retrying with the right amount is not an extra credit.
    rejected = {**owed, "arguments": {"rider_id": "R-1", "amount": 0}, "status": "rejected"}
    assert score([rejected, owed, ticket]) == 1.0


def test_has_number():
    assert has_number("That ride costs $7.50.", 7.5)
    assert has_number("Fee: 2,500 dollars", 2500)
    assert not has_number("about $7", 7.5)


def test_arguments_match():
    assert arguments_match(
        {"plan": "Member", "minutes": "50", "ebike": False}, {"plan": "member", "minutes": 50, "ebike": False}
    )
    assert arguments_match({"amount": 7.2, "rider_id": "r-1042"}, {"amount": 7.20, "rider_id": "R-1042"})
    assert not arguments_match({"amount": 7.0}, {"amount": 7.2})
    assert not arguments_match({}, {"station_id": "LS-01"})


@pytest.mark.parametrize("actual", ["false", "true", 0, 1, [], {}, None])
@pytest.mark.parametrize("expected", [False, True])
def test_arguments_match_requires_real_booleans(actual, expected):
    assert not arguments_match({"ebike": actual}, {"ebike": expected})


@pytest.mark.parametrize("actual", [float("nan"), "NaN", float("inf"), "Infinity", True, False, [], {}])
def test_arguments_match_rejects_invalid_numbers(actual):
    assert not arguments_match({"total": actual}, {"total": 1.0})


@pytest.mark.parametrize("actual", [None, [], "not an object", 7])
def test_arguments_match_rejects_non_objects(actual):
    assert not arguments_match(actual, {"station_id": "LS-01"})


def test_latency_score():
    assert latency_score([1000, 2000, 3000], 4000, 15000)[0] == 1.0
    assert latency_score([20000], 4000, 15000)[0] == 0.0
    assert 0 < latency_score([9500], 4000, 15000)[0] < 1
