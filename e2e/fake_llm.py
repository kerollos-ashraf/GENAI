"""A deterministic, rule-based stand-in for the LLM, used only by the end-to-end suite.

It drives the *real* LangGraph workflow, tools, RAG and guardrails exactly like a real model
would (it emits tool calls, then answers from the tool output), so the browser tests exercise
the whole stack offline, for free, with the same answer every run.
"""

import json
import re
import uuid
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

_CLAIM_ID = re.compile(r"\bCLM-\d+\b", re.IGNORECASE)
_POLICY = re.compile(r"\bpolicy\s+([A-Z]{0,3}-?\d+|[A-Z]+)\b", re.IGNORECASE)
_AMOUNT = re.compile(r"\$\s?(-?[\d,]+(?:\.\d+)?)")
_CITATION = re.compile(r"^\[([^\]]+)\]$", re.MULTILINE)


def _call(name: str, args: dict[str, Any]) -> AIMessage:
    return AIMessage("", tool_calls=[{"name": name, "args": args, "id": uuid.uuid4().hex}])


class RuleBasedLLM(BaseChatModel):
    @property
    def _llm_type(self) -> str:
        return "e2e-rule-based"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages: list[BaseMessage], *args, **kwargs) -> ChatResult:
        reply = self._reply(messages)
        return ChatResult(generations=[ChatGeneration(message=reply)])

    # -- decisions --------------------------------------------------------------------------

    def _reply(self, messages: list[BaseMessage]) -> AIMessage:
        last = messages[-1]
        if isinstance(last, ToolMessage):
            return AIMessage(self._answer_from_tool(last))
        question = next(
            (str(m.content) for m in reversed(messages) if isinstance(m, HumanMessage)), ""
        )
        return self._plan(question)

    def _plan(self, question: str) -> AIMessage:
        text = question.lower()
        if text.strip(" !.") in {"hi", "hello", "hey"}:
            return AIMessage("Hello! Ask me about your coverage or a claim.")
        if "file a claim" in text or "submit a claim" in text:
            return _call("submit_claim", self._claim_args(question))
        if claim := _CLAIM_ID.search(question):
            return _call("get_claim_status", {"claim_id": claim.group(0)})
        return _call("search_policy", {"query": question})

    @staticmethod
    def _claim_args(question: str) -> dict[str, Any]:
        policy = _POLICY.search(question)
        amount = _AMOUNT.search(question)
        kind = "Personal Property" if "property" in question.lower() else "Water Damage"
        return {
            "policy_number": policy.group(1) if policy else "",
            "claim_type": kind,
            "amount": float(amount.group(1).replace(",", "")) if amount else 0,
            "description": question,
        }

    # -- answers ----------------------------------------------------------------------------

    @staticmethod
    def _answer_from_tool(result: ToolMessage) -> str:
        content = str(result.content)
        if result.status == "error" or content.startswith("Error"):
            return "I couldn't do that: the claim details are invalid. Please check them."
        if result.name == "search_policy":
            citations = _CITATION.findall(content)
            if not citations:
                return "I couldn't find that in the documents."
            lines = [
                ln.strip() for ln in content.split("[" + citations[0] + "]", 1)[1].splitlines()
            ]
            body = [ln for ln in lines if ln and not ln.startswith(("Document:", "#", "["))]
            passage = body[0][:160] if body else ""
            return f"Here is what the policy says: {passage} [{citations[0]}]"
        if result.name == "get_claim_status":
            if content.startswith("No claim"):
                return content
            claim = json.loads(content)
            return f"Claim {claim['claim_id']} is {claim['status']}."
        if result.name == "submit_claim":
            confirmation = re.search(r"Confirmation ID: (CLM-\d+)", content)
            return f"Your claim has been filed. Confirmation ID: {confirmation.group(1)}."
        return content
