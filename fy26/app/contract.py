"""The API contract: request and response shapes for every route.

The harness tests your endpoint against exactly these shapes. You may change how
answers are produced; keep the shapes.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

CONTRACT_VERSION = "fy26.v1"

Category = Literal["billing", "bike_issue", "station_issue", "account", "safety", "other"]
Urgency = Literal["low", "medium", "high"]
Guardrail = Literal["prompt_injection", "unsafe"]

MAX_TEXT = 4000


class InfoResponse(BaseModel):
    student_id: str
    service: str = "lakeshore-ride-support"
    version: str
    contract: str = CONTRACT_VERSION
    model: str
    capabilities: list[str]


# Week 5 ---------------------------------------------------------------------


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=MAX_TEXT)


class ChatResponse(BaseModel):
    answer: str
    model: str


class ClassifyRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    text: str = Field(min_length=1, max_length=MAX_TEXT)


class TicketLabel(BaseModel):
    """What the model must return for a support ticket."""

    category: Category
    urgency: Urgency
    summary: str = Field(description="One sentence, at most 25 words.")


class ClassifyResponse(TicketLabel):
    id: str


# Week 6 ---------------------------------------------------------------------


class AskRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    question: str = Field(min_length=1, max_length=MAX_TEXT)


class Citation(BaseModel):
    doc_id: str


class ToolCall(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class AskResponse(BaseModel):
    id: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    abstained: bool = False
    guardrail: Guardrail | None = None


# Week 7 ---------------------------------------------------------------------


class ResolveRequest(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    case: str = Field(min_length=1, max_length=MAX_TEXT)


class Action(BaseModel):
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    status: str


class ResolveResponse(BaseModel):
    id: str
    resolution: str
    route: list[str]
    actions: list[Action] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    guardrail: Guardrail | None = None
