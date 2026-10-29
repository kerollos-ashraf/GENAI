"""Plain data objects shared between layers (no framework dependencies)."""

from dataclasses import asdict, dataclass, field
from typing import Any

# --- Chat ---------------------------------------------------------------------------------

USER_ID_PATTERN = r"^[A-Za-z0-9_\-]{1,64}$"
MAX_MESSAGE_CHARS = 2000


@dataclass(frozen=True)
class ToolCallRecord:
    name: str
    args: dict[str, Any]
    status: str
    output: str


@dataclass(frozen=True)
class ChatTurn:
    """The outcome of one user turn: the answer, its cited sources and every tool call."""

    response: str
    sources: list[str]
    tool_calls: list[ToolCallRecord]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- Knowledge base -----------------------------------------------------------------------


@dataclass(frozen=True)
class Section:
    """A citable unit of a document: a markdown section, a PDF page, a whole text file."""

    label: str
    text: str


@dataclass(frozen=True)
class RetrievedChunk:
    citation: str  # e.g. "sample_policy.md § Section 1: Home Water Damage Coverage"
    section: str
    source: str
    content: str
    score: float


@dataclass(frozen=True)
class IndexedDocument:
    content_hash: str
    chunks: int


@dataclass(frozen=True)
class DocumentInfo:
    filename: str
    size_bytes: int
    chunks: int
    indexed: bool


@dataclass
class SyncReport:
    added: list[str] = field(default_factory=list)
    updated: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)

    @property
    def changed(self) -> bool:
        return bool(self.added or self.updated or self.removed)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# --- Speech -------------------------------------------------------------------------------


@dataclass(frozen=True)
class Transcript:
    text: str
    language: str | None = None
    duration_seconds: float | None = None
