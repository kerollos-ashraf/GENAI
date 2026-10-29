"""Voice use cases: validate a recording, transcribe it, optionally ask the assistant."""

import re
from pathlib import Path

from app.domain.errors import InvalidInputError, PayloadTooLargeError
from app.domain.models import MAX_MESSAGE_CHARS, ChatTurn, Transcript
from app.domain.ports import ChatAssistant, Transcriber

ALLOWED_AUDIO = frozenset(
    {".wav", ".webm", ".mp3", ".m4a", ".mp4", ".mpeg", ".mpga", ".ogg", ".flac"}
)
_HAS_WORD = re.compile(r"\w")  # silence often transcribes as "" or "."


class VoiceService:
    def __init__(self, transcriber: Transcriber, chat: ChatAssistant, max_bytes: int) -> None:
        self._transcriber = transcriber
        self._chat = chat
        self._max_bytes = max_bytes

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def transcribe(self, audio: bytes, filename: str) -> Transcript:
        self._validate(audio, filename)
        transcript = self._transcriber.transcribe(audio, filename)
        if not _HAS_WORD.search(transcript.text):
            raise InvalidInputError("No speech detected - please try again")
        return transcript

    def ask(
        self, user_id: str, audio: bytes, filename: str, session_id: str | None = None
    ) -> tuple[Transcript, ChatTurn]:
        """Ask by voice: the transcript goes through the normal chat pipeline (guard, RAG,
        tools), so spoken and typed questions are treated identically."""
        transcript = self.transcribe(audio, filename)
        turn = self._chat.ask(user_id, transcript.text[:MAX_MESSAGE_CHARS], session_id)
        return transcript, turn

    def _validate(self, audio: bytes, filename: str) -> None:
        if Path(filename).suffix.lower() not in ALLOWED_AUDIO:
            raise InvalidInputError(
                f"Unsupported audio type. Use one of: {', '.join(sorted(ALLOWED_AUDIO))}"
            )
        if len(audio) > self._max_bytes:
            raise PayloadTooLargeError(
                f"Audio file is too large (max {self._max_bytes // (1024 * 1024)} MB)"
            )
        if not audio:
            raise InvalidInputError("Empty audio file")
