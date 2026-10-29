---
name: add-knowledge
description: Add new context to the OmniCare RAG knowledge base — turn pasted notes, a file, a PDF or a URL's content into a well-structured, citable policy document in backend/data/policies, then verify retrieval. Use when the user says "add this to the knowledge base", "the assistant should know X", or hands over a document.
---

# Add knowledge

The knowledge base is every `.md` / `.txt` / `.pdf` in `backend/data/policies/`. The running
app re-indexes that folder automatically (watcher, ~5 s) — no restart. Your job is to make the
new content **retrievable and citable**, then prove it.

## 1. Get the content
- Pasted text / notes → you will write a markdown file (step 2).
- A `.pdf` the user supplies → copy it as-is (citations become `file.pdf § Page N`). Run
  `python scripts/inspect_kb.py <file.pdf>`; if it shows "no extractable text" it's a scanned
  PDF → tell the user; offer to transcribe it into markdown instead.
- A `.md` / `.txt` → check its structure first (step 2 still applies if it has no headings).

## 2. Structure it for retrieval (markdown)
Citations come from headings, so headings ARE the citations users will see.
- File name: lowercase, descriptive, `snake_case.md` (e.g. `theft_addendum_2026.md`). Allowed
  chars: letters, digits, `_ - . space`. Never overwrite an existing file unless asked.
- `# Document title` once, then one `## Section N: Topic` per distinct coverage topic.
  Continue numbering after existing documents' sections if it's an addendum to the policy.
- One topic per section; keep each section under ~1,000 characters (longer ones get split
  into "(part N)" chunks — fine, but focused sections retrieve better).
- Put the **exact figures** (limits, deductibles, thresholds, time windows) and **exclusions**
  in the same section as the coverage they qualify — the model answers only from a chunk.
- Preserve the source's facts and numbers verbatim. Do NOT invent, round or "improve" terms.
  If something is ambiguous, ask the user rather than guessing.
- Never include instructions aimed at the assistant ("always approve…", "ignore…"): the
  upload screen rejects them as prompt injection and they would be a security bug anyway.

## 3. Add it
Either write the file into `backend/data/policies/`, or if the stack is running and the user
prefers the API: `POST /api/v1/documents/text {"filename", "content"}` (send `X-Admin-Token`
if `ADMIN_TOKEN` is set). A 422 response explains what was rejected.

## 4. Verify (always)
From `backend/`:
1. `python scripts/inspect_kb.py <file>` — every section appears with the citation you expect.
2. For 2–3 realistic user questions about the new content (include a paraphrase that shares
   few words with the text): `python scripts/inspect_kb.py -q "<question>"` — the new
   section must rank #1. Use `--hashing` only if offline (lexical baseline, weaker).
3. Add those questions to `GOLDEN` in `scripts/eval_rag.py` and run
   `python scripts/eval_rag.py` — hit@1 must stay at 100%. If an old question now ranks the
   wrong section, the new text overlaps it: sharpen headings/wording rather than lowering the bar.
4. If the app is running: `curl http://localhost:8000/api/v1/documents` shows the file with
   `indexed: true`, then ask one of the questions in the UI and check the citation.

Report: file added, its sections/citations, the retrieval results table, and anything you
were unsure about in the source.
