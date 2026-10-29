"""The knowledge base (Facade): keeps the vector index in sync with the documents folder.

It coordinates three collaborators, each with one job:
  * `FileSystemDocumentStore` - where documents live
  * `Chunker`                 - how a document becomes cited chunks
  * `ChromaVectorIndex`       - where chunks are embedded and searched

Sync is incremental: each chunk carries its document's fingerprint, so only new or changed
files are embedded, edited files have their old chunks replaced, and deleted files are
removed. Unreadable files are reported in `SyncReport.failed` and never break the rest.

With a guard, every new or changed file is screened for indirect prompt injection before it
is embedded - whether it was uploaded or dropped straight into the folder. A rejected file is
reported in `SyncReport.failed`, and any chunks from an earlier clean version are removed.
"""

import logging
import threading
from pathlib import Path

from langchain_core.embeddings import Embeddings

from app.domain.errors import InvalidInputError
from app.domain.models import (
    DocumentInfo,
    IndexedDocument,
    RetrievedChunk,
    Section,
    SyncReport,
)
from app.domain.ports import DocumentStore, InputGuard, VectorIndex
from app.infrastructure.document_store import FileSystemDocumentStore
from app.infrastructure.vector_index import ChromaVectorIndex
from app.rag.chunker import Chunker
from app.security.screening import injection_reason

logger = logging.getLogger(__name__)


class KnowledgeBase:
    def __init__(
        self,
        store: DocumentStore,
        index: VectorIndex,
        chunker: Chunker,
        guard: InputGuard | None = None,
    ) -> None:
        self.store = store
        self.index = index
        self.chunker = chunker
        self.guard = guard
        self._lock = threading.RLock()

    @classmethod
    def create(
        cls,
        docs_dir: Path,
        embeddings: Embeddings,
        collection_name: str,
        persist_dir: Path | None = None,
        chunker: Chunker | None = None,
        guard: InputGuard | None = None,
    ) -> "KnowledgeBase":
        """Factory wiring the default adapters (filesystem + Chroma), then an initial sync."""
        chunker = chunker or Chunker()
        kb = cls(
            FileSystemDocumentStore(docs_dir, chunker.loaders.extensions),
            ChromaVectorIndex(embeddings, collection_name, persist_dir),
            chunker,
            guard,
        )
        kb.sync()
        return kb

    # -- Retriever port --------------------------------------------------------------------

    def search(self, query: str, k: int = 3) -> list[RetrievedChunk]:
        return self.index.search(query, k)

    # -- DocumentManager port --------------------------------------------------------------

    def parse(self, filename: str, data: bytes) -> list[Section]:
        """Validate the filename and extract sections, without storing anything."""
        name = self.chunker.loaders.validate_filename(filename)
        return self.chunker.sections(name, data)

    def list_documents(self) -> list[DocumentInfo]:
        indexed = self.index.indexed_documents()
        return [
            DocumentInfo(
                filename=f.name,
                size_bytes=f.size_bytes,
                chunks=indexed[f.name].chunks if f.name in indexed else 0,
                indexed=f.name in indexed,
            )
            for f in self.store.files()
        ]

    def add_document(self, filename: str, data: bytes) -> SyncReport:
        name = self.chunker.loaders.validate_filename(filename)
        if not self.chunker.sections(name, data):
            raise InvalidInputError("Document contains no extractable text")
        with self._lock:
            self.store.write(name, data)
            return self.sync()

    def delete_document(self, filename: str) -> SyncReport:
        name = self.chunker.loaders.validate_filename(filename)
        with self._lock:
            self.store.delete(name)
            return self.sync()

    def sync(self, force: bool = False) -> SyncReport:
        """Bring the index in line with the folder. Only changed files are embedded."""
        with self._lock:
            if force:
                self.index.reset()
            indexed = self.index.indexed_documents()
            report = SyncReport()
            on_disk = self.store.files()
            for file in on_disk:
                self._sync_file(file.name, report, indexed.get(file.name))
            for name in set(indexed) - {f.name for f in on_disk}:
                self.index.delete(name)
                report.removed.append(name)
        if report.changed:
            logger.info("Knowledge base synced: %s", report.to_dict())
        return report

    def _sync_file(self, name: str, report: SyncReport, previous: IndexedDocument | None) -> None:
        data = self.store.read(name)
        if previous and previous.content_hash == self.chunker.fingerprint(data):
            report.unchanged.append(name)
            return
        try:
            if self.guard and (
                reason := injection_reason(self.chunker.sections(name, data), self.guard)
            ):
                if previous:  # an edit poisoned a file that was clean before: drop old chunks
                    self.index.delete(name)
                raise InvalidInputError(reason)
            chunks = self.chunker.chunk(name, data)
            if not chunks:
                raise InvalidInputError("no extractable text")
        except InvalidInputError as exc:
            report.failed[name] = str(exc)
            logger.warning("Skipping %s: %s", name, exc)
            return
        self.index.replace(name, chunks)
        (report.updated if previous else report.added).append(name)
