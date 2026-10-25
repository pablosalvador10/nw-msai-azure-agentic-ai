"""Week 5: free-form chat. One instruction, one model call, no tools, no memory."""

from app.contract import ChatRequest, ChatResponse
from app.state import AppState

INSTRUCTIONS = """You are the support assistant for Lakeshore Ride, a bike-share service.
Answer in at most three sentences. If you are not sure, say so."""


async def chat(state: AppState, request: ChatRequest) -> ChatResponse:
    """Week 5: answer free text with one model call."""
    answer = await state.models.chat(INSTRUCTIONS, request.message)
    return ChatResponse(answer=answer, model=state.models.name)
