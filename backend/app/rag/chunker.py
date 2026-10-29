"""Turns a document into cited, embeddable chunks."""

import hashlib
from dataclasses import dataclass, field

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.domain.models import Section
from app.rag.loaders import LoaderRegistry

# Bump when chunking/loading logic changes: it is part of every document's fingerprint, so
# all documents are re-processed automatically on the next sync.
CHUNKER_VERSION = "2"


@dataclass
class Chunker:
    """Splits each section into ~`max_chars` parts with overlap.

    Every chunk starts with a ``Document: <title>`` line (contextual chunk header), so a
    page that never repeats its subject - e.g. page 2 of a policy addendum PDF, which doesn't
    repeat the addendum's name - is still retrieved for questions about it.
    Citations look like ``<file> § <section>``, with ``(part N)`` for split sections.
    """

    loaders: LoaderRegistry = field(default_factory=LoaderRegistry.default)
    max_chars: int = 1200
    overlap: int = 150
    version: str = CHUNKER_VERSION

    def fingerprint(self, data: bytes) -> str:
        return hashlib.sha256(self.version.encode() + b"\0" + data).hexdigest()[:16]

    def sections(self, filename: str, data: bytes) -> list[Section]:
        return self.loaders.for_file(filename).sections(data)

    def chunk(self, filename: str, data: bytes) -> list[Document]:
        loader = self.loaders.for_file(filename)
        sections = loader.sections(data)
        if not sections:
            return []
        title = loader.title(filename, data)
        fingerprint = self.fingerprint(data)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_chars, chunk_overlap=self.overlap
        )
        chunks = []
        for section in sections:
            parts = (
                splitter.split_text(section.text)
                if len(section.text) > self.max_chars
                else [section.text]
            )
            for n, part in enumerate(parts, 1):
                label = f"{section.label} (part {n})" if len(parts) > 1 else section.label
                chunks.append(
                    Document(
                        page_content=f"Document: {title}\n{part}",
                        metadata={
                            "source": filename,
                            "section": label,
                            "citation": f"{filename} § {label}",
                            "doc_hash": fingerprint,
                            "title": title,
                        },
                    )
                )
        return chunks
