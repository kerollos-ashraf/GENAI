"""Groq Whisper adapter for the `Transcriber` port (free tier, same GROQ_API_KEY)."""

import os

from app.domain.errors import ServiceUnavailableError, UpstreamServiceError
from app.domain.models import Transcript

# Vocabulary hint: helps Whisper spell domain terms and IDs ("CLM-8821", not "claim 88 21").
WHISPER_PROMPT = (
    "OmniCare insurance assistant. Claim IDs like CLM-8821, policy numbers like POL-1092. "
    "Terms: deductible, coverage, water damage, personal property, appraisal."
)


class SpeechNotConfiguredError(ServiceUnavailableError):
    pass


class SpeechError(UpstreamServiceError):
    pass


class GroqWhisperTranscriber:  # pragma: no cover - calls the real API
    def __init__(self, model: str, prompt: str = WHISPER_PROMPT) -> None:
        self._model = model
        self._prompt = prompt

    def transcribe(self, audio: bytes, filename: str) -> Transcript:
        if not os.environ.get("GROQ_API_KEY", "").strip():
            raise SpeechNotConfiguredError(
                "Voice input needs GROQ_API_KEY (free at https://console.groq.com/keys)."
            )
        from groq import Groq, GroqError

        try:
            result = Groq().audio.transcriptions.create(
                model=self._model,
                file=(filename, audio),
                prompt=self._prompt,
                response_format="verbose_json",
                temperature=0.0,
            )
        except GroqError as exc:
            raise SpeechError(f"Transcription failed: {exc}") from exc
        return Transcript(
            text=(result.text or "").strip(),
            language=getattr(result, "language", None),
            duration_seconds=getattr(result, "duration", None),
        )
