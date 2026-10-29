"""Document loaders (Strategy pattern) and their registry.

Each loader turns raw bytes of one format into citable `Section`s and a title. Supporting a
new format (e.g. .docx) means writing one loader and registering it - nothing else changes.
"""

import io
import re
from pathlib import Path
from typing import Protocol

from langchain_text_splitters import MarkdownHeaderTextSplitter

from app.domain.errors import InvalidInputError
from app.domain.models import Section

OVERVIEW = "Overview"


class DocumentError(InvalidInputError):
    """A document can't be accepted: bad name, unsupported type, empty, unreadable."""


class DocumentLoader(Protocol):
    extensions: frozenset[str]

    def sections(self, data: bytes) -> list[Section]: ...

    def title(self, filename: str, data: bytes) -> str: ...


def _decode_utf8(data: bytes) -> str:
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentError("Text documents must be UTF-8 encoded") from exc


def _title_from_filename(filename: str) -> str:
    return re.sub(r"[_\-]+", " ", Path(filename).stem).strip()


class MarkdownLoader:
    """One section per heading (#, ##, ###); the deepest heading names the section."""

    extensions = frozenset({".md", ".markdown"})
    _HEADERS = [("#", "h1"), ("##", "h2"), ("###", "h3")]

    def sections(self, data: bytes) -> list[Section]:
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on=self._HEADERS, strip_headers=True)
        result = []
        for doc in splitter.split_text(_decode_utf8(data)):
            body = doc.page_content.strip()
            if body:  # skip a title with nothing under it
                meta = doc.metadata
                result.append(
                    Section(meta.get("h3") or meta.get("h2") or meta.get("h1") or OVERVIEW, body)
                )
        return result

    def title(self, filename: str, data: bytes) -> str:
        match = re.search(r"^#\s+(.+)$", data.decode("utf-8-sig", errors="ignore"), re.M)
        return match.group(1).strip() if match else _title_from_filename(filename)


class PlainTextLoader:
    """The whole file is one section."""

    extensions = frozenset({".txt"})

    def sections(self, data: bytes) -> list[Section]:
        text = _decode_utf8(data).strip()
        return [Section(OVERVIEW, text)] if text else []

    def title(self, filename: str, data: bytes) -> str:
        return _title_from_filename(filename)


class PdfLoader:
    """One section per page with text ("Page N"). Scanned PDFs yield no sections."""

    extensions = frozenset({".pdf"})

    def sections(self, data: bytes) -> list[Section]:
        from pypdf import PdfReader

        try:
            pages = PdfReader(io.BytesIO(data)).pages
            texts = [(page.extract_text() or "").strip() for page in pages]
        except Exception as exc:  # corrupt or encrypted PDF
            raise DocumentError(f"Could not read PDF: {exc}") from exc
        return [Section(f"Page {i}", text) for i, text in enumerate(texts, 1) if text]

    def title(self, filename: str, data: bytes) -> str:
        return _title_from_filename(filename)


class LoaderRegistry:
    """Maps file extensions to loaders and owns the filename policy."""

    _NAME_CHARS = r"[A-Za-z0-9][A-Za-z0-9 _.\-]{0,100}"

    def __init__(self, loaders: list[DocumentLoader]) -> None:
        self._by_extension = {ext: loader for loader in loaders for ext in loader.extensions}
        exts = "|".join(re.escape(e.lstrip(".")) for e in self._by_extension)
        self._filename_re = re.compile(rf"^{self._NAME_CHARS}\.({exts})$", re.IGNORECASE)

    @classmethod
    def default(cls) -> "LoaderRegistry":
        return cls([MarkdownLoader(), PlainTextLoader(), PdfLoader()])

    @property
    def extensions(self) -> frozenset[str]:
        return frozenset(self._by_extension)

    def validate_filename(self, filename: str) -> str:
        name = filename.strip()
        if Path(name).name != name or not self._filename_re.match(name):
            raise DocumentError(
                "Invalid filename. Use letters, digits, spaces, '.', '_' or '-' and one of: "
                + ", ".join(sorted(self.extensions))
            )
        return name

    def for_file(self, filename: str) -> DocumentLoader:
        loader = self._by_extension.get(Path(filename).suffix.lower())
        if loader is None:
            raise DocumentError(f"Unsupported file type: {filename}")
        return loader
