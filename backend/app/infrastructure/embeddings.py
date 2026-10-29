"""Embedding back-ends and their factory.

* ``fastembed`` - local ONNX embeddings (default ``BAAI/bge-small-en-v1.5``): free, CPU-only.
* ``hashing``   - deterministic bag-of-words hashing. No downloads; used by the test suite
  and as an automatic offline fallback.
"""

import hashlib
import logging
import math
import re
from dataclasses import dataclass

from langchain_core.embeddings import Embeddings

from app.config import Settings

logger = logging.getLogger(__name__)

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from",
    "how", "i", "if", "in", "is", "it", "my", "of", "on", "or", "the", "to", "what",
    "when", "with", "you", "your", "much", "many", "am", "me", "will", "under",
}  # fmt: skip


class HashingEmbeddings(Embeddings):
    """Deterministic, dependency-free embeddings (unigrams + bigrams hashed into a vector)."""

    def __init__(self, dim: int = 512) -> None:
        self.dim = dim

    @staticmethod
    def _tokens(text: str) -> list[str]:
        tokens = []
        for word in re.findall(r"[a-z0-9]+", text.lower()):
            if word in _STOPWORDS:
                continue
            if len(word) > 3 and word.endswith("s"):  # naive plural stemming: pipes -> pipe
                word = word[:-1]
            tokens.append(word)
        return tokens

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dim
        tokens = self._tokens(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:], strict=False)]
        for feature in features:
            digest = int(hashlib.md5(feature.encode()).hexdigest(), 16)
            vector[digest % self.dim] += 1.0 if (digest >> 64) % 2 else -1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FastEmbedEmbeddings(Embeddings):  # pragma: no cover - needs a model download
    """Adapter: exposes ``fastembed.TextEmbedding`` through LangChain's `Embeddings` API."""

    def __init__(self, model_name: str) -> None:
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model_name)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [v.tolist() for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return next(iter(self._model.query_embed(text))).tolist()


@dataclass(frozen=True)
class EmbeddingProfile:
    """The embedding function plus the vector collection it owns. Each model gets its own
    collection, so switching models (or falling back) never mixes vector dimensions."""

    embeddings: Embeddings
    collection_name: str


def create_embeddings(settings: Settings) -> EmbeddingProfile:
    """Factory: build the configured embeddings, falling back to hashing if FastEmbed
    can't load (e.g. offline on first start)."""
    if settings.embeddings_provider == "hashing":
        return EmbeddingProfile(HashingEmbeddings(), settings.kb_collection)
    try:  # pragma: no cover - needs a model download
        return EmbeddingProfile(
            FastEmbedEmbeddings(settings.embeddings_model), settings.kb_collection
        )
    except Exception:  # pragma: no cover
        logger.exception("FastEmbed unavailable; falling back to hashing embeddings")
        return EmbeddingProfile(HashingEmbeddings(), settings.kb_collection + "_fallback")
