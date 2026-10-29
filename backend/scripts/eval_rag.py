"""Retrieval quality check: does the right policy section come back for each golden question?

Usage (from backend/):
    python scripts/eval_rag.py              # real local embeddings (FastEmbed)
    python scripts/eval_rag.py --hashing    # offline hashing embeddings
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import Settings  # noqa: E402
from app.infrastructure.embeddings import create_embeddings  # noqa: E402
from app.rag.knowledge_base import KnowledgeBase  # noqa: E402

WATER = "sample_policy.md § Section 1: Home Water Damage Coverage"
PROPERTY = "sample_policy.md § Section 2: Personal Property Protection"
THEFT = "theft_addendum_2026.md § Section 3: Theft and Burglary Coverage"
STAY = "theft_addendum_2026.md § Section 4: Temporary Accommodation"

# question -> the sections that correctly answer it (the first is the ideal one)
GOLDEN: list[tuple[str, tuple[str, ...]]] = [
    ("Is water damage from a burst pipe covered?", (WATER,)),
    ("What's my deductible if a pipe bursts?", (WATER,)),
    ("Are floods covered?", (WATER,)),
    ("I had a slow leak under the sink for months, can I claim?", (WATER,)),
    ("What is the maximum payout for water damage?", (WATER,)),
    ("Is my jewelry covered?", (PROPERTY,)),
    ("My laptop was stolen, what's the coverage limit?", (PROPERTY, THEFT)),
    ("Do I need a receipt for a $3,000 TV?", (PROPERTY,)),
    ("What's the total limit for furniture and electronics?", (PROPERTY,)),
    ("Do expensive items need an appraisal?", (PROPERTY,)),
    ("Someone broke in and stole things, do I need a police report?", (THEFT,)),
    ("Will you pay for a hotel if my house is unlivable after a covered loss?", (STAY,)),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--hashing", action="store_true", help="use offline hashing embeddings")
    parser.add_argument("-k", type=int, default=2)
    parser.add_argument("--threshold", type=float, default=1.0, help="minimum hit@1 rate")
    args = parser.parse_args()

    settings = Settings(
        _env_file=None,
        embeddings_provider="hashing" if args.hashing else "fastembed",
        chroma_dir=None,
    )
    profile = create_embeddings(settings)
    retriever = KnowledgeBase.create(
        settings.policies_dir, profile.embeddings, collection_name="eval"
    )

    hit1 = hitk = 0
    print(f"{'':2} {'score':>6}  {'question':<58} top hit")
    for question, expected in GOLDEN:
        results = retriever.search(question, k=args.k)
        cites = [r.citation for r in results]
        ok1 = bool(cites) and cites[0] in expected
        hit1 += ok1
        hitk += any(c in expected for c in cites)
        top = results[0] if results else None
        mark = "✅" if ok1 else "❌"
        section = top.section if top else "-"
        print(f"{mark} {top.score if top else 0:>6.3f}  {question:<58} {section}")

    n = len(GOLDEN)
    print(f"\nhit@1 = {hit1}/{n} ({hit1 / n:.0%})   hit@{args.k} = {hitk}/{n} ({hitk / n:.0%})")
    return 0 if hit1 / n >= args.threshold else 1


if __name__ == "__main__":
    raise SystemExit(main())
