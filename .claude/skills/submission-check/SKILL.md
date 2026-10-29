---
name: submission-check
description: Audit the repo against the GenAI Engineer assessment requirements before submitting (endpoints, RAG citations, tools, safety, Docker, README, tests, walkthrough). Use when the user asks if the project is ready to submit or what is missing.
---

# Submission check

Go through every requirement, verify it **by looking at the code or running it** (not from
memory), and output a checklist with ✅ / ❌ and a one-line evidence pointer (file:line or
command output) for each.

**Functional**
- [ ] `POST /api/v1/chat` accepts `{"user_id","message"}` → `{"response","sources","tool_calls"}`
- [ ] `GET /api/v1/health` → `{"status":"healthy"}`
- [ ] Policy RAG ingests `sample_policy.md`, answers include document citations
- [ ] `get_claim_status(claim_id)` reads `mock_claims.json`
- [ ] `submit_claim(policy_number, claim_type, amount, description)` validates with Pydantic,
      appends to `mock_claims.json`, returns a confirmation ID
- [ ] Prompt-injection attempts rejected; data types validated
- [ ] Framework is one of LangGraph / LangChain / CrewAI / ADK / LiveKit / Pipecat
- [ ] Web chat UI with message history and source citations

**Submission**
- [ ] `/frontend` and `/backend` separation
- [ ] Dockerfile per service + root `docker-compose.yml`; `docker compose up` launches everything
- [ ] README: architecture diagram, 2-minute run instructions, framework rationale, curl examples
- [ ] pytest covers endpoints, tool calls, RAG retrieval — run it and paste the summary line
- [ ] Walkthrough: `docs/WALKTHROUGH.md` with real screenshots in `docs/screenshots/` (or a video link)
- [ ] Zero cost: local vector store, free-tier/local LLM, no paid services
- [ ] No secrets committed: `git ls-files | grep -i env` shows only `.env.example`

Finish with the top 3 things to fix (if any), ordered by reviewer impact.
