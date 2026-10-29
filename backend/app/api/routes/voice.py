from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import Voice
from app.api.schemas import TranscriptionResponse, VoiceChatResponse
from app.domain.models import USER_ID_PATTERN

router = APIRouter(prefix="/api/v1", tags=["voice"])


async def _read(audio: UploadFile, voice: Voice) -> tuple[bytes, str]:
    # Read one byte past the limit so the service can tell "too large" apart from "at limit".
    return await audio.read(voice.max_bytes + 1), audio.filename or "audio.wav"


@router.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe(audio: Annotated[UploadFile, File()], voice: Voice) -> TranscriptionResponse:
    """Speech -> text (Groq Whisper). Accepts wav/webm/mp3/m4a/ogg/flac."""
    data, name = await _read(audio, voice)
    transcript = await run_in_threadpool(voice.transcribe, data, name)
    return TranscriptionResponse(
        text=transcript.text,
        language=transcript.language,
        duration_seconds=transcript.duration_seconds,
    )


@router.post("/chat/voice", response_model=VoiceChatResponse)
async def voice_chat(
    audio: Annotated[UploadFile, File()],
    user_id: Annotated[str, Form(pattern=USER_ID_PATTERN)],
    voice: Voice,
    session_id: Annotated[str | None, Form(pattern=USER_ID_PATTERN)] = None,
) -> VoiceChatResponse:
    """Ask by voice: transcribe, then run the normal chat pipeline (guard, RAG, tools)."""
    data, name = await _read(audio, voice)
    transcript, turn = await run_in_threadpool(voice.ask, user_id, data, name, session_id)
    return VoiceChatResponse(**turn.to_dict(), transcript=transcript.text)
