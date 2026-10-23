"""Lakeshore Ride business logic: fares, stations, credits and tickets.

Plain Python, no AI. Agents call these functions as tools; the harness checks
their results. Deterministic on purpose: same input, same output.
"""

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

DATA_DIR = Path(__file__).parent / "data"

Plan = Literal["single", "day_pass", "member", "student"]

# (unlock fee, classic $/min, included classic minutes, e-bike $/min)
_PRICING: dict[str, tuple[float, float, int, float]] = {
    "single": (1.25, 0.20, 0, 0.40),
    "day_pass": (0.00, 0.20, 45, 0.25),
    "member": (0.00, 0.15, 45, 0.18),
    "student": (0.00, 0.15, 60, 0.15),
}
FARE_CAP = 50.00
CREDIT_LIMIT = 25.00


def quote_fare(plan: str, minutes: int, ebike: bool = False) -> dict[str, Any]:
    """Ride fee for one ride, following the 'Plans and pricing' handbook page."""
    if plan not in _PRICING:
        return {"error": f"Unknown plan '{plan}'. Use one of: {', '.join(_PRICING)}."}
    if minutes < 0:
        return {"error": "minutes must be zero or positive."}

    unlock, classic_rate, included, ebike_rate = _PRICING[plan]
    if ebike:
        billable = minutes
        fee = unlock + ebike_rate * billable
    else:
        billable = max(0, minutes - included)
        fee = unlock + classic_rate * billable
    total = round(min(fee, FARE_CAP), 2)
    return {
        "plan": plan,
        "minutes": minutes,
        "ebike": ebike,
        "billable_minutes": billable,
        "total": total,
        "capped": fee > FARE_CAP,
    }


@lru_cache
def _stations() -> dict[str, dict[str, Any]]:
    raw = json.loads((DATA_DIR / "stations.json").read_text(encoding="utf-8"))
    return {s["id"]: s for s in raw["stations"]}


def get_station(station_id: str) -> dict[str, Any]:
    """Live availability for one station (from the course snapshot)."""
    station = _stations().get(station_id.strip().upper())
    if station is None:
        return {"error": f"No station with id '{station_id}'. Ids look like LS-07."}
    return dict(station)


def list_stations() -> list[dict[str, Any]]:
    """Every station, with availability (from the course snapshot)."""
    return [dict(s) for s in _stations().values()]


def distance_km(a: dict[str, Any], b: dict[str, Any]) -> float:
    """Great-circle distance between two stations (haversine formula)."""
    lat1, lon1, lat2, lon2 = map(math.radians, (a["lat"], a["lon"], b["lat"], b["lon"]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def issue_credit(rider_id: str, amount: float, reason: str) -> dict[str, Any]:
    """Ride credit for a rider. Above the agent limit the case goes to a supervisor."""
    amount = round(float(amount), 2)
    if amount <= 0:
        return {"status": "rejected", "error": "amount must be positive."}
    status = "issued" if amount <= CREDIT_LIMIT else "escalated"
    return {"status": status, "rider_id": rider_id, "amount": amount, "reason": reason}


def open_ticket(category: str, station_id: str, summary: str) -> dict[str, Any]:
    """Maintenance ticket for the operations team."""
    allowed = {"bike_repair", "station_repair", "rebalancing"}
    if category not in allowed:
        return {"status": "rejected", "error": f"category must be one of {sorted(allowed)}."}
    return {"status": "open", "category": category, "station_id": station_id.upper(), "summary": summary}
