"""Chat use case. Two implementations of the `ChatAssistant` port:

* `ChatService`            - runs the agent workflow and formats the turn.
* `UnavailableChatService` - Null Object used when no LLM is configured: the API still
                             starts (health, documents, voice transcription keep working)
                             and chat requests get a clear 503 instead of a crash.
"""

import logging

from app.agent.response import TurnFormatter
from app.agent.workflow import AssistantWorkflow
from app.domain.errors import ServiceUnavailableError, UpstreamServiceError
from app.domain.models import ChatTurn

logger = logging.getLogger(__name__)

GENERIC_FAILURE = "The assistant failed to respond. Please retry."


def describe_failure(exc: Exception) -> str:
    """User-facing reason for a failed turn. Errors returned by the LLM provider's API (they
    carry an HTTP `status_code`: no credits, invalid key, rate limit, unknown model) are
    actionable, so their message is shown. Anything else stays generic, so internals never
    leak."""
    status = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None
    )
    if isinstance(status, int):
        detail = " ".join(str(exc).split())[:300]
        return f"The AI provider rejected the request (HTTP {status}): {detail}"
    return GENERIC_FAILURE


class ChatService:
    def __init__(self, workflow: AssistantWorkflow, formatter: TurnFormatter | None = None) -> None:
        self._workflow = workflow
        self._formatter = formatter or TurnFormatter()

    def ask(self, user_id: str, message: str, session_id: str | None = None) -> ChatTurn:
        thread_id = f"{user_id}:{session_id or 'default'}"
        try:
            messages = self._workflow.run(thread_id, message)
        except Exception as exc:
            logger.exception("Agent failure for user %s", user_id)
            raise UpstreamServiceError(describe_failure(exc)) from exc
        return self._formatter.format(messages)


class UnavailableChatService:
    def __init__(self, reason: str) -> None:
        self.reason = reason

    def ask(self, user_id: str, message: str, session_id: str | None = None) -> ChatTurn:
        raise ServiceUnavailableError(self.reason)
