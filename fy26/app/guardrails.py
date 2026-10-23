"""Input and output guardrails (Week 10).

Cheap checks that run before any model call. They are a first layer, not the
whole defense: Foundry also applies content filters to every model call, and a
production system would add Prompt Shields and evaluations on top.
"""

import re

from app.contract import Guardrail

_INJECTION = [
    r"ignore (all|any|the|your|previous|prior|above|earlier)\b.{0,40}\b(instructions|rules|prompt)",
    r"disregard\b.{0,40}\b(instructions|rules|prompt)",
    r"\b(system|developer) (prompt|message|instructions)\b",
    r"\byou are now\b",
    r"\b(jailbreak|developer mode|dan mode)\b",
    r"\breveal\b.{0,30}\b(prompt|instructions)\b",
    r"\brepeat\b.{0,20}\b(text|words|everything) above\b",
]
_UNSAFE = [
    r"\b(steal|stealing|hotwire|hot-wire)\b",
    r"\b(disable|remove|defeat|bypass|cut)\b.{0,30}\b(gps|tracker|lock|dock)\b",
]

REFUSALS: dict[str, str] = {
    "prompt_injection": "I can only help with Lakeshore Ride questions, and I can't change how I work.",
    "unsafe": "I can't help with that. If you need help with a ride, I'm happy to assist.",
}


def screen(text: str) -> Guardrail | None:
    """Return the guardrail that fires for this input, or None if it looks fine."""
    lowered = text.lower()
    if any(re.search(p, lowered) for p in _INJECTION):
        return "prompt_injection"
    if any(re.search(p, lowered) for p in _UNSAFE):
        return "unsafe"
    return None


def is_content_filter_error(exc: Exception) -> bool:
    """Foundry blocks harmful prompts with a 400 'content_filter' error. Treat it as a refusal."""
    text = str(exc).lower()
    return "content_filter" in text or "content management policy" in text
