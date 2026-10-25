"""Week 5: ticket triage with structured output.

The model must return JSON that matches TicketLabel. The Responses API enforces
the schema, so `category` can only be one of the six allowed values.

This is the starting version: the model only sees the category names. In the
Week 5 lab you measure it with the harness, then improve INSTRUCTIONS.
"""

from app.contract import ClassifyRequest, ClassifyResponse, TicketLabel
from app.state import AppState

INSTRUCTIONS = """You classify support tickets for Lakeshore Ride, a bike-share service.
Return the ticket's category, its urgency and a one-sentence summary."""


async def classify(state: AppState, request: ClassifyRequest) -> ClassifyResponse:
    """Week 5: triage a ticket into category, urgency and summary with structured output."""
    if state.offline:
        label = offline_label(request.text)
    else:
        label = await state.models.parse(INSTRUCTIONS, request.text, TicketLabel)
    return ClassifyResponse(id=request.id, **label.model_dump())


_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("safety", ("hurt", "injur", "crash", "bleeding", "accident", "unsafe")),
    ("billing", ("charge", "refund", "fee", "credit", "pass", "price", "bill", "paid", "$")),
    ("station_issue", ("dock", "station", "kiosk")),
    ("bike_issue", ("brake", "tire", "chain", "battery", "seat", "pedal", "bike")),
    ("account", ("account", "email", "password", "login", "delete", "privacy")),
]


def offline_label(text: str) -> TicketLabel:
    """Keyword rules. Deliberately naive: the model should beat this easily."""
    lowered = text.lower()
    category = next((cat for cat, words in _KEYWORDS if any(w in lowered for w in words)), "other")
    urgency = {"safety": "high", "billing": "medium", "bike_issue": "medium", "station_issue": "medium"}.get(
        category, "low"
    )
    return TicketLabel(category=category, urgency=urgency, summary=text.strip().split(".")[0][:150])
