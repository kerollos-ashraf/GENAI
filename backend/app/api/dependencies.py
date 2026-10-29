"""FastAPI dependencies: hand each route the service it needs from the container."""

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request

from app.container import Container
from app.domain.ports import ChatAssistant
from app.services.document_service import DocumentService
from app.services.voice_service import VoiceService


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_chat(container: Annotated[Container, Depends(get_container)]) -> ChatAssistant:
    return container.chat


def get_documents(container: Annotated[Container, Depends(get_container)]) -> DocumentService:
    return container.documents


def get_voice(container: Annotated[Container, Depends(get_container)]) -> VoiceService:
    return container.voice


def require_admin(
    container: Annotated[Container, Depends(get_container)],
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    """If ADMIN_TOKEN is set, document changes need a matching `X-Admin-Token` header."""
    expected = container.settings.admin_token
    if expected and not (x_admin_token and secrets.compare_digest(x_admin_token, expected)):
        raise HTTPException(status_code=401, detail="Missing or invalid X-Admin-Token")


Chat = Annotated[ChatAssistant, Depends(get_chat)]
Documents = Annotated[DocumentService, Depends(get_documents)]
Voice = Annotated[VoiceService, Depends(get_voice)]
AdminOnly = [Depends(require_admin)]
