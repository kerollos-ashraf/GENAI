# OmniCare Assistant — project guide for Claude

GenAI Engineer technical assessment: a prototype customer assistant for **OmniCare Financial**
(insurance). React chat UI → FastAPI → LangGraph agent with policy RAG (citations) and two
claim tools. Must run with `docker compose up` at zero cost.

## Layout (layered; dependencies point inward)
- `backend/app/`
  - `main.py` app factory: builds the `Container`, mounts routers. No logic.
  - `container.py` **composition root** - the only place concrete classes are chosen and wired
  - `api/` HTTP only: `routes/` (chat, documents, voice), `schemas.py`, `dependencies.py`,
    `errors.py` (domain error → HTTP status, one place; catch-all → JSON 500 with a ref id)
  - `services/` use cases: `ChatService` (+ `UnavailableChatService` null object),
    `DocumentService` (upload policy + injection screening), `VoiceService`
  - `domain/` framework-free: `models.py`, `claims.py`, `errors.py`, `ports.py` (Protocols)
  - `agent/` LangGraph: `workflow.py` (`guard → refuse | agent ⇄ tools`), `tools.py`,
    `prompts.py`, `response.py` (turn → `ChatTurn`)
  - `rag/` `loaders.py` (per-format Strategy + registry), `chunker.py`, `knowledge_base.py`
    (Facade: store + chunker + index, incremental sync), `watcher.py`
  - `infrastructure/` adapters: Chroma index, filesystem store, JSON claims repo, embeddings
    factory, LLM provider registry, Groq Whisper
  - `security/guard.py` prompt-injection guard (English + Arabic) for messages;
    `security/screening.py` applies it to every document (uploads AND folder drops, via
    `KnowledgeBase.sync`). `tests/test_guardrails.py` pins blocked AND allowed phrasings -
    add a case to both lists whenever you touch a pattern.
- `backend/data/policies/` — the knowledge base (add documents here; indexed automatically)
- `backend/data/` — `mock_claims.json` (mutable), `mock_claims.seed.json` (pristine copy)
- `backend/tests/` — pytest, fully offline; `test_architecture.py` enforces the layering
- `backend/scripts/` — `eval_rag.py` (retrieval quality), `inspect_kb.py` (chunks/citations)
- `frontend/` — React 19 + TypeScript (Vite). `src/api/client.ts` (API gateway, injected via
  `ClientContext`), `src/hooks/` (use cases: chat, knowledge base, recorder, health,
  preferences), `src/components/` (presentational), `src/lib/` (pure text helpers, speech
  controller, storage), `src/styles/` (design tokens incl. dark theme, base). Each component
  imports its own CSS and uses tokens only - no raw colours. API responses are validated at
  runtime (`src/api/validate.ts`). Tests sit next to the code (`*.test.ts(x)`, Vitest +
  Testing Library); coverage thresholds are enforced.
  `nginx/default.conf.template` serves the build and proxies `/api` (adds `X-Admin-Token`).

## Design rules
- Inner layers (`domain`, `services`, `rag`, `agent`, `security`) never import FastAPI;
  `domain`/`services` never import `api`. `tests/test_architecture.py` fails if they do.
- Depend on ports (`domain/ports.py`), not adapters. New adapter → wire it in `container.py`.
- Services raise `domain.errors`; never `HTTPException` (except auth in `api/dependencies.py`).
- Extend by registration, not editing: new LLM provider → `@register_provider` in
  `infrastructure/llm.py`; new file format → a loader in `rag/loaders.py`
  registered in `LoaderRegistry.default()`.
- Frontend components never call `fetch` - go through `OmniCareClient` (via `useClient()`).
  State and side effects live in hooks; components stay presentational. Render model output
  as Markdown only (never `dangerouslySetInnerHTML`).

## Commands (run from `backend/`)
- Install: `pip install -r requirements-dev.txt`
- Tests: `python -m pytest`; frontend (from `frontend/`): `npm ci` once, then `npm run lint`,
  `npm run typecheck`, `npm run coverage` (tests + thresholds), `npm run format:check`
  (fix with `npm run format`)
- Lint/format: `ruff check --fix . && ruff format .`
- RAG eval: `python scripts/eval_rag.py` (add `--hashing` to run offline)
- Run API: `uvicorn app.main:app --reload` (needs `.env` with an LLM key, see `.env.example`)
- Run UI (from `frontend/`): `npm run dev -- --port 8501` (proxies `/api` to `localhost:8000`)
- Browser tests (from `e2e/`): `python -m pytest` (real UI + backend, rule-based fake LLM;
  `HEADED=1` to watch). Fake backend for manual UI work: `python e2e/server.py --port 8000 --data-dir .e2e-data`
- Everything: `docker compose up --build` from repo root → UI http://localhost:8501, API docs http://localhost:8000/docs

## Conventions
- Every tool argument is validated by a Pydantic model; invalid input must never touch `mock_claims.json`.
- Tests must stay offline and deterministic: use `tests/conftest.py` helpers (`scripted`, `tool_call`,
  `retriever`, `claims_file`). Never hit a real LLM or download models in tests.
- Never edit `mock_claims.seed.json`; tests copy it into a temp dir.
- API contract is fixed by the assessment: request `{user_id, message}`, response
  `{response, sources, tool_calls}`. `session_id` is an optional, backwards-compatible extra.
- Keep the graph shape documented in `agent/workflow.py` docstring and README diagram in sync.
- Never commit `.env` or API keys.

## Definition of done (before saying a change is finished)
1. `ruff check . && ruff format --check .` clean; for frontend changes `npm run lint`,
   `npm run typecheck`, `npm run coverage` and `npm run format:check` clean
2. `python -m pytest` green
3. New behaviour has a test (endpoint, tool, RAG or guardrail as relevant); user-facing UI
   changes also get a case in `e2e/test_ui.py` and `cd e2e && python -m pytest` passes
4. README updated if setup, endpoints or architecture changed

Use the project skills: `/e2e-test` (Playwright suite + Playwright MCP walkthrough), `/add-knowledge`, `/run-checks`, `/add-agent-tool`, `/rag-eval`,
`/submission-check`, `/walkthrough`. Use the `code-reviewer` and `security-auditor` agents before submitting.
