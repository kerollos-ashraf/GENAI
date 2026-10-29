"""Chroma adapter: the only module that knows about Chroma (and its private collection API)."""

from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.domain.models import IndexedDocument, RetrievedChunk


class ChromaVectorIndex:
    """Stores cited chunks, grouped by source document, with cosine similarity search."""

    def __init__(
        self, embeddings: Embeddings, collection_name: str, persist_dir: Path | None = None
    ) -> None:
        self._store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=str(persist_dir) if persist_dir else None,
            collection_metadata={"hnsw:space": "cosine"},
        )

    @property
    def _collection(self):
        return self._store._collection

    def indexed_documents(self) -> dict[str, IndexedDocument]:
        """{source: IndexedDocument} for everything currently in the index."""
        counts: dict[str, int] = {}
        hashes: dict[str, str] = {}
        for meta in self._collection.get(include=["metadatas"])["metadatas"]:
            source = meta["source"]
            counts[source] = counts.get(source, 0) + 1
            hashes.setdefault(source, meta.get("doc_hash", ""))
        return {s: IndexedDocument(hashes[s], counts[s]) for s in counts}

    def replace(self, source: str, chunks: list[Document]) -> None:
        """Atomically (from the caller's view) swap a document's chunks for new ones."""
        self.delete(source)
        self._store.add_documents(chunks, ids=[f"{source}::{i}" for i in range(len(chunks))])

    def delete(self, source: str) -> None:
        self._collection.delete(where={"source": source})

    def reset(self) -> None:
        self._store.reset_collection()

    def count(self) -> int:
        return self._collection.count()

    def texts(self, source: str) -> list[str]:
        return self._collection.get(where={"source": source})["documents"]

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        return [
            RetrievedChunk(
                citation=doc.metadata["citation"],
                section=doc.metadata["section"],
                source=doc.metadata["source"],
                content=doc.page_content,
                score=round(1 - float(distance), 4),  # cosine distance -> similarity
            )
            for doc, distance in self._store.similarity_search_with_score(query, k=k)
        ]
