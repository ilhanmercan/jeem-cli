from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


# ── Request models ──────────────────────────────────────────────

class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str


class Message(BaseModel):
    parts: list[TextPart]
    id: str
    role: Literal["user", "assistant"]


class ChatRequest(BaseModel):
    id: str
    messages: list[Message]


# ── Response / SSE models ───────────────────────────────────────

class TextDelta(BaseModel):
    type: Literal["text-delta"] = "text-delta"
    id: str
    delta: str


class TextEnd(BaseModel):
    type: Literal["text-end"] = "text-end"
    id: str


class FollowupsData(BaseModel):
    suggestions: list[str]


class DataFollowups(BaseModel):
    type: Literal["data-followups"] = "data-followups"
    id: str
    data: FollowupsData


class SummaryData(BaseModel):
    status: str


class DataSummary(BaseModel):
    type: Literal["data-summary"] = "data-summary"
    id: str
    data: SummaryData


class FinishMetadata(BaseModel):
    chatId: str
    messageUid: str
    routeMetadata: None = None


class Finish(BaseModel):
    type: Literal["finish"] = "finish"
    finishReason: str
    messageMetadata: FinishMetadata


SSEEvent = Annotated[
    TextDelta | TextEnd | DataFollowups | DataSummary | Finish,
    Field(discriminator="type"),
]


# ── Session models ──────────────────────────────────────────────

class Session(BaseModel):
    name: str
    chat_id: str
    messages: list[Message] = []
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
