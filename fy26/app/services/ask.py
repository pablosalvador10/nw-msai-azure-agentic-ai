"""Week 6: answering rider questions from the handbook.

This is the starting version: classic retrieve-then-generate.

    question -> search the handbook (top 3 passages) -> one model call -> answer + citations

It has no tools, so it cannot quote exact fares or read live station data, and it
never decides to search again. In the Week 6 lab you replace it with an agent
that calls tools (Microsoft Agent Framework), then compare harness scores.
"""

import re

from pydantic import BaseModel, Field

from app import domain
from app.contract import AskRequest, AskResponse, Citation, ToolCall
from app.guardrails import REFUSALS, is_content_filter_error, screen
from app.rag import doc_ids
from app.state import AppState
from app.tools import handbook_search

INSTRUCTIONS = """You answer rider questions for Lakeshore Ride, a bike-share service,
using the handbook passages provided. Cite the doc_id of every passage you used."""


class AskAnswer(BaseModel):
    answer: str
    citations: list[str] = Field(description="doc_id values of the passages you used.")
    abstained: bool = Field(description="True when the handbook does not answer the question.")


async def ask(state: AppState, request: AskRequest) -> AskResponse:
    """Week 6: answer a rider's question from the handbook, with citations."""
    if guardrail := screen(request.question):
        return AskResponse(id=request.id, answer=REFUSALS[guardrail], abstained=True, guardrail=guardrail)
    if state.offline:
        return await offline_ask(state, request)

    hits = await handbook_search(state, request.question, top_k=3)
    passages = "\n\n".join(f"[{h['doc_id']}] {h['title']} > {h['section']}\n{h['text']}" for h in hits)
    prompt = f"Handbook passages:\n{passages}\n\nQuestion: {request.question}"
    try:
        parsed = await state.models.parse(INSTRUCTIONS, prompt, AskAnswer)
    except Exception as exc:
        if is_content_filter_error(exc):
            return AskResponse(id=request.id, answer=REFUSALS["unsafe"], abstained=True, guardrail="unsafe")
        raise

    known = doc_ids()
    return AskResponse(
        id=request.id,
        answer=parsed.answer,
        citations=[Citation(doc_id=d) for d in dict.fromkeys(parsed.citations) if d in known],
        tool_calls=[ToolCall(name="search_handbook", arguments={"query": request.question})],
        abstained=parsed.abstained,
    )


_PLAN_WORDS = {"day pass": "day_pass", "member": "member", "student": "student", "single": "single"}


async def offline_ask(state: AppState, request: AskRequest) -> AskResponse:
    """No model: route by regex, retrieve by keyword overlap. Enough to test the contract."""
    question = request.question
    calls: list[ToolCall] = []

    if station := re.search(r"\bLS-\d{2}\b", question.upper()):
        info = domain.get_station(station.group())
        calls.append(ToolCall(name="get_station", arguments={"station_id": station.group()}))
        return AskResponse(id=request.id, answer=str(info), tool_calls=calls)

    minutes = re.search(r"(\d+)[- ]?min", question.lower())
    plan = next((p for word, p in _PLAN_WORDS.items() if word in question.lower()), None)
    if minutes and plan:
        args = {"plan": plan, "minutes": int(minutes.group(1)), "ebike": "e-bike" in question.lower()}
        quote = domain.quote_fare(**args)
        calls.append(ToolCall(name="quote_fare", arguments=args))
        return AskResponse(id=request.id, answer=f"${quote['total']:.2f}", tool_calls=calls)

    hits = await handbook_search(state, question, top_k=2)
    if not hits or hits[0]["score"] < 0.2:
        return AskResponse(id=request.id, answer="I don't know.", abstained=True)
    top = hits[0]
    return AskResponse(
        id=request.id,
        answer=top["text"][:400],
        citations=[Citation(doc_id=top["doc_id"])],
        tool_calls=[ToolCall(name="search_handbook", arguments={"query": question})],
    )
