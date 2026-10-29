from fastapi import APIRouter
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import Chat
from app.api.schemas import ChatRequest, ChatResponse, HealthResponse

router = APIRouter(prefix="/api/v1", tags=["chat"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="healthy")


@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, assistant: Chat) -> ChatResponse:
    """Ask a question; returns the answer, cited sources and every tool call made."""
    turn = await run_in_threadpool(assistant.ask, req.user_id, req.message, req.session_id)
    return ChatResponse.model_validate(turn.to_dict())
