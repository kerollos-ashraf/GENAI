---
name: rag-eval
description: Evaluate and improve policy RAG retrieval quality (hit-rate of the right policy section for each golden question). Use when policy documents change, chunking/embeddings/top-k change, or answers cite the wrong section.
---

# RAG evaluation

1. Run `python scripts/eval_rag.py` from `backend/` (real FastEmbed model). Use `--hashing` when
   offline — it's a lexical baseline, so paraphrases like "laptop stolen" can miss; only the
   real-embedding run is held to 100%. It prints each golden question, the expected section, the top hit and its score,
   then the hit@1 and hit@k rates; it exits non-zero if hit@1 < the threshold (default 1.0).
2. If a document in `backend/data/policies/` was added or changed, add 2–3 golden questions per new section to
   `GOLDEN` in `scripts/eval_rag.py`, including paraphrases that don't share keywords with the
   text (e.g. "my laptop was stolen" → Personal Property). Mirror the key ones in
   `tests/test_rag.py`.
3. When a question misses, try in this order: improve the section heading/wording in the
   policy chunk metadata, adjust `RAG_TOP_K`, change `EMBEDDINGS_MODEL`, and only then change
   chunking in `app/rag/chunker.py` (bump `CHUNKER_VERSION` so existing documents are
   re-processed). Re-run after each change and report the before/after table.
4. Citations must stay in the format `<file> § <section heading>` — the frontend and tests
   depend on it.
