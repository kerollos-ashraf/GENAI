"""The LangGraph workflow:

    START -> guard --(blocked)--> refuse -> END
               \\--(allowed)--> agent <-> tools   (ReAct loop, capped per turn)
                                  \\-> END

Conversation memory is a LangGraph checkpointer thread per (user_id, session_id).
"""

import logging
from typing import Annotated, TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    SystemMessage,
    trim_messages,
)
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.prompts import REDACTED_MESSAGE, SYSTEM_PROMPT
from app.domain.ports import InputGuard
from app.security.guard import REFUSAL_MESSAGE

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    blocked: bool


class AssistantWorkflow:
    def __init__(
        self,
        llm: BaseChatModel,
        tools: list[BaseTool],
        guard: InputGuard,
        *,
        history_window: int = 20,
        max_tool_rounds: int = 5,
        system_prompt: str = SYSTEM_PROMPT,
        checkpointer: BaseCheckpointSaver | None = None,
    ) -> None:
        self._llm = llm
        self._llm_with_tools = llm.bind_tools(tools)
        self._tools = tools
        self._guard = guard
        self._history_window = history_window
        self._max_tool_rounds = max_tool_rounds
        self._system_prompt = system_prompt
        self._graph = self._build(checkpointer or InMemorySaver())

    def run(self, thread_id: str, message: str) -> list[AnyMessage]:
        state = self._graph.invoke(
            {"messages": [HumanMessage(message)], "blocked": False},
            config={"configurable": {"thread_id": thread_id}},
        )
        return state["messages"]

    # -- graph -----------------------------------------------------------------------------

    def _build(self, checkpointer: BaseCheckpointSaver):
        graph = StateGraph(AgentState)
        graph.add_node("guard", self._guard_node)
        graph.add_node("refuse", self._refuse_node)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", ToolNode(self._tools, handle_tool_errors=True))

        graph.add_edge(START, "guard")
        graph.add_conditional_edges("guard", lambda s: "refuse" if s["blocked"] else "agent")
        graph.add_edge("refuse", END)
        graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
        return graph.compile(checkpointer=checkpointer)

    # -- nodes -----------------------------------------------------------------------------

    def _guard_node(self, state: AgentState) -> dict:
        verdict = self._guard.check(str(state["messages"][-1].content))
        if not verdict.allowed:
            logger.warning("Blocked input (reason=%s)", verdict.reason)
        return {"blocked": not verdict.allowed}

    @staticmethod
    def _refuse_node(state: AgentState) -> dict:
        # Replace the blocked message in place (same id) so the injection attempt never
        # reaches the LLM on later turns of this conversation.
        blocked = state["messages"][-1]
        redacted = HumanMessage(content=REDACTED_MESSAGE, id=blocked.id)
        return {"messages": [redacted, AIMessage(content=REFUSAL_MESSAGE)]}

    def _agent_node(self, state: AgentState) -> dict:
        history = trim_messages(
            state["messages"],
            strategy="last",
            token_counter=len,  # count messages, not tokens
            max_tokens=self._history_window,
            start_on="human",
            include_system=False,
        )
        # Stop runaway tool loops: after N tool rounds this turn, force a final answer.
        model = (
            self._llm
            if self._tool_rounds_this_turn(state["messages"]) >= self._max_tool_rounds
            else self._llm_with_tools
        )
        return {"messages": [model.invoke([SystemMessage(self._system_prompt), *history])]}

    @staticmethod
    def _tool_rounds_this_turn(messages: list[AnyMessage]) -> int:
        rounds = 0
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                break
            if isinstance(message, AIMessage) and message.tool_calls:
                rounds += 1
        return rounds
