"""Turns the messages of one graph run into the API-facing `ChatTurn`."""

import json
from typing import Any

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, ToolMessage

from app.agent.tools import TOOL_SEARCH
from app.domain.models import ChatTurn, ToolCallRecord

# Some models (e.g. gpt-oss) emit 【…】 lenticular brackets; normalise to [..].
_BRACKETS = str.maketrans({"【": "[", "】": "]"})


class TurnFormatter:
    def __init__(self, max_output_chars: int = 500) -> None:
        self._max_output_chars = max_output_chars

    def format(self, messages: list[AnyMessage]) -> ChatTurn:
        turn = self._current_turn(messages)
        results = {m.tool_call_id: m for m in turn if isinstance(m, ToolMessage)}
        tool_calls: list[ToolCallRecord] = []
        retrieved: list[str] = []
        for message in turn:
            if not isinstance(message, AIMessage):
                continue
            for call in message.tool_calls:
                result = results.get(call["id"])
                tool_calls.append(self._record(call, result))
                if call["name"] == TOOL_SEARCH and result is not None and result.artifact:
                    retrieved.extend(c for c in result.artifact if c not in retrieved)

        answer = self._answer_text(turn)
        cited = [c for c in retrieved if c in answer]
        # Prefer the sources the model actually cited; fall back to everything retrieved.
        return ChatTurn(response=answer, sources=cited or retrieved, tool_calls=tool_calls)

    @staticmethod
    def _current_turn(messages: list[AnyMessage]) -> list[AnyMessage]:
        """Everything after the latest human message."""
        start = max(i for i, m in enumerate(messages) if isinstance(m, HumanMessage))
        return messages[start + 1 :]

    @staticmethod
    def _answer_text(turn: list[AnyMessage]) -> str:
        final = turn[-1] if turn and isinstance(turn[-1], AIMessage) else AIMessage("")
        text = final.text
        text = text() if callable(text) else text  # `.text` is a method in older langchain
        return text.translate(_BRACKETS)

    def _record(self, call: dict, result: ToolMessage | None) -> ToolCallRecord:
        return ToolCallRecord(
            name=call["name"],
            args=call["args"],
            status=result.status if result is not None else "error",
            output=self._truncate(result.content if result is not None else ""),
        )

    def _truncate(self, content: Any) -> str:
        text = content if isinstance(content, str) else json.dumps(content, default=str)
        if len(text) <= self._max_output_chars:
            return text
        return text[: self._max_output_chars] + "…"
