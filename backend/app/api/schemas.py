"""HTTP request/response models (the API contract)."""

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.domain.models import MAX_MESSAGE_CHARS, USER_ID_PATTERN


class ChatRequest(BaseModel):
    user_id: str = Field(pattern=USER_ID_PATTERN, examples=["usr_123"])
    message: str = Field(
        min_length=1, max_length=MAX_MESSAGE_CHARS, examples=["Are burst pipes covered?"]
    )
    session_id: str | None = Field(
        default=None,
        pattern=USER_ID_PATTERN,
        description="Optional: start a fresh conversation without changing user_id.",
    )

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message must not be blank")
        return value.strip()


class ToolCall(BaseModel):
    name: str
    args: dict[str, Any]
    status: str
    output: str


class ChatResponse(BaseModel):
    response: str
    sources: list[str]
    tool_calls: list[ToolCall]


class HealthResponse(BaseModel):
    status: str


class DocumentInfoOut(BaseModel):
    filename: str
    size_bytes: int
    chunks: int
    indexed: bool


class DocumentList(BaseModel):
    documents: list[DocumentInfoOut]
    total_chunks: int


class SyncResult(BaseModel):
    added: list[str]
    updated: list[str]
    removed: list[str]
    unchanged: list[str]
    failed: dict[str, str]


class TextDocument(BaseModel):
    filename: str = Field(examples=["home_theft_addendum.md"])
    content: str = Field(min_length=1, examples=["# Theft Addendum\n\n## Section 3: Theft\n..."])


class TranscriptionResponse(BaseModel):
    text: str
    language: str | None = None
    duration_seconds: float | None = None


class VoiceChatResponse(ChatResponse):
    transcript: str
