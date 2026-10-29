# Testing

All suites run **offline and deterministically**. No real LLM is called and no model is
downloaded during tests. The real LangGraph graph, RAG pipeline, tools, FastAPI app and React
build run unchanged; only the LLM, the embeddings (in backend tests) and speech-to-text are
replaced by fakes.

| Suite | Count | Run it |
|---|---|---|
| Backend (pytest) | 146 | `cd backend && pip install -r requirements-dev.txt && python -m pytest` |
| Frontend (Vitest + Testing Library) | 58 | `cd frontend && npm ci && npm run coverage` |
| Browser end-to-end (Playwright) | 21 | see [Browser tests](#browser-tests) |

## Backend

The tests use deterministic hashing embeddings and a scripted fake LLM that emits real tool
calls, so the full graph runs: guard → agent → ToolNode → tools → answer.

| File | Covers |
|---|---|
| `test_api.py` | health contract; chat → RAG with citations in `sources`; claim status; claim submission writes the file; invalid tool arguments reported back to the model; injection refused without an LLM call and redacted from memory; per-user memory; request validation (422); 503 when no LLM is configured; LLM-provider errors explained, internal errors kept generic; any unexpected exception → JSON 500 with a reference ID and no internals |
| `test_tools.py` | lookup, normalisation, unknown and malformed IDs; submission, confirmation ID, round-trip lookup; 8 invalid-input cases that write nothing; 20 concurrent submissions |
| `test_rag.py` | section chunking and citations; the right section ranks first for 6 queries; idempotent re-sync |
| `test_knowledge_base.py` | Markdown/text/PDF chunking and citations; contextual title headers; long-section splitting; unsafe filenames; dropped-in files indexed and searchable; edits replace old chunks; deletions removed; unchanged files not re-embedded; broken files skipped; the folder watcher; **injection screening of dropped files**, including a clean file edited into a poisoned one |
| `test_documents_api.py` | list, upload, text, delete and reindex endpoints; the agent answers from a just-uploaded document; bad name, type, empty or oversized files rejected; poisoned uploads rejected; a poisoned file dropped into the folder is never indexed; admin token enforced |
| `test_voice_api.py` | transcription endpoint; voice chat runs the full pipeline; spoken injection blocked without an LLM call; audio type, size and empty-file validation; silence detection; missing key → 503, upstream error → 502 |
| `test_guardrails.py` | 23 attacks blocked (English and Arabic, paraphrased leaks, full-width, zero-width, diacritics); 18 legitimate questions allowed, including phrasings older patterns wrongly refused; Arabic normalisation |
| `test_architecture.py` | layering rules from the import graph; domain error → HTTP status mapping; a new LLM provider and a new file format plug in by registration alone; configurable guard rules; Null Object chat service; opt-in sampling temperature |

**Retrieval quality:** `python scripts/eval_rag.py` scores 12 golden questions (hit@1, hit@k)
with the real embeddings; add `--hashing` for the offline baseline.

**Lint and format:** `ruff check . && ruff format --check .` (run from `backend/`; also covers
`e2e/` and `scripts/` in CI).

## Frontend

```bash
cd frontend
npm ci
npm run coverage       # Vitest; fails below the thresholds in vite.config.ts
npm run lint           # ESLint: strict type-aware TypeScript, React hooks, jsx-a11y
npm run typecheck      # tsc
npm run format:check   # Prettier
```

Coverage: about 92% of lines.

| Area | Covers |
|---|---|
| API client | chat contract; response validation; backend error details and validation messages; proxy-down and network failures; cancellation; URL-encoded filenames; multipart uploads |
| Text helpers | citation numbering, citation splitting, speech-text cleaning, sentence splitting (English and Arabic) |
| Components | Markdown rendering without raw HTML; numbered citations; tool calls; failed answers with Try again; safe links; spoken badge; composer (Enter / Shift+Enter, busy, counter, notices); suggestions; sidebar settings, Escape and focus |
| Speech | sentence queueing, pause/resume, one answer at a time, natural-voice ranking, remembered voice |
| Whole app (fake API) | suggestion → cited answer; one session ID per conversation; Try again; Stop; copy; offline state; theme; document upload, dismiss and delete; voice recording → transcription → question; failed transcription; cancelled recording; blocked microphone |

## Browser tests

```bash
pip install -r e2e/requirements.txt
python -m playwright install chromium
cd frontend && npm ci && cd ../e2e
python -m pytest              # set HEADED=1 to watch the browser
```

The harness starts the real backend with a rule-based fake LLM (`e2e/fake_llm.py`,
`e2e/server.py`) on a private copy of the data, builds the React app, serves it with
`vite preview` (which proxies `/api` like nginx does), and drives it in Chromium with a fake
microphone. It finishes in about 30 seconds.

The 21 scenarios:
- **Start screen:** suggestions and the online/offline status.
- **Answers:** a cited answer with numbered tags, and `$` amounts rendered as plain text.
- **Claims:** lookup (found and unknown), a saved claim submission, and an invalid claim that is rejected with nothing saved.
- **Safety:** prompt-injection refusal, a poisoned upload rejected, and the backend-down state.
- **Composer:** Shift+Enter adds a line instead of sending.
- **Conversation:** new conversation, copy answer, and the jump-to-latest button.
- **Voice:** the voice player, a voice question through a fake microphone, a cancelled recording, and the remembered reply mode.
- **Knowledge base:** upload a document, ask about it, then delete it.
- **Theme:** the dark theme, applied before first paint.
- **Phone:** the phone layout with its settings drawer.

**Exploratory checks with a real model:** `.mcp.json` registers the
[Playwright MCP](https://github.com/microsoft/playwright-mcp) server, and the `/e2e-test`
Claude Code skill walks the same cases plus real-model checks (answer quality, Arabic replies).
The config uses `cmd /c npx` for Windows; on macOS/Linux use
`"command": "npx", "args": ["-y", "@playwright/mcp@0.0.83"]`.
