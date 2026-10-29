---
name: run-checks
description: Run the full quality gate for the OmniCare project (ruff, pytest, RAG eval, frontend typecheck/tests/format, compose config). Use after any code change, before committing, or when the user asks "is everything still working?".
---

# Run checks

Run these from `backend/` in order and stop at the first failure to fix it:

1. `ruff check .` — fix with `ruff check --fix .`; anything left, fix by hand.
2. `ruff format --check .` — fix with `ruff format .`.
3. `python -m pytest` — all tests must pass (including `test_architecture.py`, which
   enforces the layering). On failure, read the failing test first; it is the
   spec. Don't weaken an assertion to make it pass unless the requirement really changed.
4. `python scripts/eval_rag.py --hashing --threshold 0.8` — offline lexical baseline. If the
   machine has internet, also run `python scripts/eval_rag.py` (real embeddings), which must
   score hit@1 = 100%.
5. Frontend, from `frontend/` (`npm ci` first if `node_modules` is missing):
   `npm run format:check` (fix with `npm run format`), `npm run lint`, `npm run typecheck`,
   `npm run coverage` (fails below the thresholds in `vite.config.ts`), `npx vite build`.
6. Browser tests when the UI or API changed: `cd ../e2e && python -m pytest`.
7. From the repo root: `docker compose config -q` — compose file must be valid.

Also lint the Python outside `backend/`: `ruff check ../e2e ../scripts`.

Report back as a short table: check → pass/fail → what you fixed. If Docker is not
available, say so rather than skipping silently.
