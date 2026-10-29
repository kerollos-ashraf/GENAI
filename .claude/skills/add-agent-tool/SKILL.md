---
name: add-agent-tool
description: Add a new tool to the OmniCare LangGraph agent (e.g. cancel_claim, list_policies) with Pydantic validation, registration, prompt update and tests. Use whenever the user wants the assistant to do a new action or look up new data.
---

# Add an agent tool

Follow the existing pattern exactly — `get_claim_status` / `submit_claim` are the reference.

1. **Schema** — in `backend/app/domain/claims.py` (or a new `domain/` module) add a Pydantic
   input model. Every field needs a `description` (the LLM reads it), strict constraints
   (`pattern`, `gt/le`, `min_length/max_length`, `Literal`) and `mode="before"` validators to
   normalise casing/whitespace.
2. **Data access** — declare what the tool needs as a small Protocol in `domain/ports.py`,
   implement it in `infrastructure/` (writes use the lock + atomic `os.replace` pattern of
   `JsonClaimsRepository._write`), and wire it in `container.py`.
3. **Tool** — in `backend/app/agent/tools.py` add a `TOOL_*` name constant, a method on
   `AssistantToolkit` and a `StructuredTool.from_function(..., args_schema=YourModel)` entry in
   `tools()`. Return a short string the LLM can quote; handle "not found" as a normal return.
4. **Prompt** — add one numbered capability line to `SYSTEM_PROMPT` in `backend/app/agent/prompts.py`,
   including when NOT to call it. Destructive actions must require the user to confirm first.
5. **Guardrails** — if the tool changes state, consider whether `security/guard.py` needs a pattern
   for abusive phrasings, and add a test case to `tests/test_guardrails.py`.
6. **Tests** (required):
   - `tests/test_tools.py`: happy path, normalisation, each invalid field (parametrize), and
     "nothing written on invalid input".
   - `tests/test_api.py`: an end-to-end turn using `scripted(tool_call("your_tool", {...}), AIMessage(...))`
     asserting `tool_calls[0]["name"]` and `status`.
7. Update the README "Agent tools" table and run `/run-checks`.
