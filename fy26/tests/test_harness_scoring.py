import pytest

from harness.scoring import arguments_match, fact_score, has_number, latency_score, normalize


def test_normalize():
    assert normalize("7 a.m. to 10 p.m.") == "7amto10pm"
    assert normalize("$2,500") == "$2500"
    assert normalize("$0.75") == "$0.75"


def test_fact_score_partial_credit():
    facts = [["$16", "16 dollars"], ["24 hours"]]
    assert fact_score("A Day Pass is $16 and lasts 24 hours.", facts) == 1.0
    assert fact_score("A Day Pass is $16.", facts) == 0.5


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
