"""Inspect the knowledge base: how documents are chunked/cited and what a query retrieves.

Usage (from backend/):
    python scripts/inspect_kb.py                       # every document -> its chunks
    python scripts/inspect_kb.py theft_addendum.md     # one document
    python scripts/inspect_kb.py -q "Is burglary covered?" [-k 3] [--hashing]
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.rag.chunker import Chunker  # noqa: E402


def show_chunks(folder: Path, only: str | None) -> int:
    chunker = Chunker()
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in chunker.loaders.extensions)
    if only:
        files = [p for p in files if p.name == only]
        if not files:
            print(f"{only} not found in {folder}")
            return 1
    for path in files:
        chunks = chunker.chunk(path.name, path.read_bytes())
        print(f"\n=== {path.name}: {len(chunks)} chunk(s)")
        for c in chunks:
            preview = " ".join(c.page_content.split())[:110]
            print(f"  [{c.metadata['citation']}] ({len(c.page_content)} chars) {preview}")
        if not chunks:
            print("  !! no extractable text - this file will not be searchable")
    return 0


def show_query(settings: Settings, query: str, k: int) -> int:
    from app.infrastructure.embeddings import create_embeddings
    from app.rag.knowledge_base import KnowledgeBase

    profile = create_embeddings(settings)
    kb = KnowledgeBase.create(settings.policies_dir, profile.embeddings, collection_name="inspect")
    print(f"\nQuery: {query!r}")
    for i, r in enumerate(kb.search(query, k=k), 1):
        print(f"  {i}. {r.score:.3f}  [{r.citation}]  {' '.join(r.content.split())[:90]}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document", nargs="?", help="only show this file's chunks")
    parser.add_argument("-q", "--query", help="run a retrieval query instead")
    parser.add_argument("-k", type=int, default=3)
    parser.add_argument("--hashing", action="store_true", help="offline hashing embeddings")
    args = parser.parse_args()
    settings = Settings(
        _env_file=None,
        embeddings_provider="hashing" if args.hashing else "fastembed",
        chroma_dir=None,
    )
    if args.query:
        return show_query(settings, args.query, args.k)
    return show_chunks(settings.policies_dir, args.document)


if __name__ == "__main__":
    raise SystemExit(main())
