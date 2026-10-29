"""Ports: the interfaces the application depends on (Dependency Inversion).

Services, tools and the agent are written against these Protocols; the concrete adapters
live in `app/infrastructure`. Swapping Chroma for Qdrant, the JSON file for Postgres or
Groq for another speech API means adding an adapter - no service code changes.
Each Protocol is deliberately small (Interface Segregation): e.g. the agent's search tool
only needs `Retriever.search`, not the whole knowledge-base management API.
"""

from collections.abc import Hashable
from typing import Protocol

from langchain_core.documents import Document

from app.domain.claims import Claim, ClaimSubmission
from app.domain.models import (
    ChatTurn,
    DocumentInfo,
    IndexedDocument,
    RetrievedChunk,
    Section,
    SyncReport,
    Transcript,
)


class ClaimsRepository(Protocol):
    def get(self, claim_id: str) -> Claim: ...

    def submit(self, submission: ClaimSubmission) -> Claim: ...


class Retriever(Protocol):
    def search(self, query: str, k: int) -> list[RetrievedChunk]: ...


class DocumentManager(Protocol):
    def parse(self, filename: str, data: bytes) -> list[Section]: ...

    def list_documents(self) -> list[DocumentInfo]: ...

    def add_document(self, filename: str, data: bytes) -> SyncReport: ...

    def delete_document(self, filename: str) -> SyncReport: ...

    def sync(self, force: bool = False) -> SyncReport: ...


class StoredDocument(Protocol):
    name: str
    size_bytes: int


class DocumentStore(Protocol):
    """Where knowledge-base documents live (a folder today; S3 tomorrow)."""

    def files(self) -> list[StoredDocument]: ...

    def signature(self) -> Hashable: ...

    def read(self, name: str) -> bytes: ...

    def write(self, name: str, data: bytes) -> None: ...

    def delete(self, name: str) -> None: ...


class VectorIndex(Protocol):
    """Where chunks are embedded and searched (Chroma today; Qdrant/FAISS tomorrow)."""

    def indexed_documents(self) -> dict[str, IndexedDocument]: ...

    def replace(self, source: str, chunks: list[Document]) -> None: ...

    def delete(self, source: str) -> None: ...

    def reset(self) -> None: ...

    def search(self, query: str, k: int) -> list[RetrievedChunk]: ...


class Transcriber(Protocol):
    def transcribe(self, audio: bytes, filename: str) -> Transcript: ...


class GuardVerdict(Protocol):
    allowed: bool
    reason: str | None


class InputGuard(Protocol):
    def check(self, text: str) -> GuardVerdict: ...


class ChatAssistant(Protocol):
    def ask(self, user_id: str, message: str, session_id: str | None = None) -> ChatTurn: ...
