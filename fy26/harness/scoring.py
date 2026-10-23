"""Small, pure scoring helpers. Unit-tested in tests/test_harness_scoring.py."""

import math
import re
import statistics
from typing import Any


def normalize(text: str) -> str:
    """Lowercase, '7 a.m.' -> '7am', '2,500' -> '2500', no whitespace."""
    text = text.lower()
    text = re.sub(r"(?<=[a-z])\.", "", text)
    text = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return re.sub(r"\s+", "", text)


def fact_score(answer: str, facts: list[list[str]]) -> float:
    """Share of facts present. Each fact is a list of acceptable phrasings."""
    if not facts:
        return 1.0
    norm = normalize(answer)
    found = sum(any(normalize(option) in norm for option in options) for options in facts)
    return found / len(facts)


def numbers_in(text: str) -> list[float]:
    cleaned = re.sub(r"(?<=\d),(?=\d{3})", "", text)
    return [float(n) for n in re.findall(r"-?\d+(?:\.\d+)?", cleaned)]


def has_number(text: str, value: float, tolerance: float = 0.005) -> bool:
    return any(abs(n - value) <= tolerance for n in numbers_in(text))


def arguments_match(actual: dict[str, Any], expected: dict[str, Any]) -> bool:
    """Every expected argument is present with an equivalent value."""
    if not isinstance(actual, dict):
        return False
    for key, want in expected.items():
        got = actual.get(key)
        if got is None:
            return False
        if isinstance(want, bool):
            if got is not want:
                return False
        elif isinstance(want, (int, float)):
            if isinstance(got, bool):
                return False
            try:
                number = float(got)
                if not math.isfinite(number) or not math.isfinite(want) or abs(number - want) > 0.01:
                    return False
            except (OverflowError, TypeError, ValueError):
                return False
        elif str(got).strip().lower() != str(want).strip().lower():
            return False
    return True


def latency_score(latencies_ms: list[float], good_ms: float, bad_ms: float) -> tuple[float, float]:
    """1.0 at or below good_ms, 0.0 at or above bad_ms, linear between. Returns (score, p50)."""
    if not latencies_ms:
        return 0.0, 0.0
    p50 = statistics.median(latencies_ms)
    if p50 <= good_ms:
        return 1.0, p50
    if p50 >= bad_ms:
        return 0.0, p50
    return (bad_ms - p50) / (bad_ms - good_ms), p50


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
