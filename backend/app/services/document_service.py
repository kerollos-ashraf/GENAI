"""Knowledge-base management use cases, with the upload policy (size, readability, and
indirect prompt-injection screening) enforced before anything is stored.

The knowledge base screens again on every sync (covering files dropped into the folder);
checking here as well means a poisoned upload is refused with a clear 422 and never even
written to disk.
"""

from app.domain.errors import InvalidInputError, PayloadTooLargeError
from app.domain.models import DocumentInfo, SyncReport
from app.domain.ports import DocumentManager, InputGuard
from app.security.screening import injection_reason


class DocumentService:
    def __init__(self, documents: DocumentManager, guard: InputGuard, max_bytes: int) -> None:
        self._documents = documents
        self._guard = guard
        self._max_bytes = max_bytes

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def list(self) -> list[DocumentInfo]:
        return self._documents.list_documents()

    def add(self, filename: str, data: bytes) -> SyncReport:
        name = filename.strip()
        self._screen(name, data)
        report = self._documents.add_document(name, data)
        if name in report.failed:
            raise InvalidInputError(report.failed[name])
        return report

    def delete(self, filename: str) -> SyncReport:
        return self._documents.delete_document(filename)

    def reindex(self, full: bool = False) -> SyncReport:
        return self._documents.sync(force=full)

    def _screen(self, filename: str, data: bytes) -> None:
        if len(data) > self._max_bytes:
            raise PayloadTooLargeError(f"File exceeds {self._max_bytes} bytes")
        sections = self._documents.parse(filename, data)
        if not sections:
            raise InvalidInputError("Document contains no extractable text")
        if reason := injection_reason(sections, self._guard):
            raise InvalidInputError(reason)
