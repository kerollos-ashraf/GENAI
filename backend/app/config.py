"""Application settings, loaded from environment variables / .env."""

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

DEFAULT_MODELS: dict[str, str] = {
    "groq": "openai/gpt-oss-120b",
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5",
    "ollama": "llama3.1",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: Literal["groq", "openai", "anthropic", "ollama"] = "groq"
    llm_model: str | None = None
    llm_temperature: float | None = None  # unset = provider default (works with every model)
    ollama_base_url: str = "http://localhost:11434"

    # RAG
    embeddings_provider: Literal["fastembed", "hashing"] = "fastembed"
    embeddings_model: str = "BAAI/bge-small-en-v1.5"
    policies_dir: Path = DATA_DIR / "policies"  # drop .md / .txt / .pdf files here
    chroma_dir: Path | None = DATA_DIR / "chroma"
    rag_top_k: int = 3
    kb_watch_interval: float = 5.0  # seconds between folder checks; 0 disables the watcher
    max_document_bytes: int = 2_000_000
    # If set, uploading/deleting documents requires the header `X-Admin-Token: <value>`.
    admin_token: str | None = None
    kb_collection_name: str | None = None  # override (tests); default derives from the model

    # Voice (speech-to-text via Groq Whisper - free tier, uses GROQ_API_KEY)
    stt_model: str = "whisper-large-v3-turbo"
    max_audio_bytes: int = 15 * 1024 * 1024  # ~ several minutes of compressed audio

    # Tools / data
    claims_path: Path = DATA_DIR / "mock_claims.json"

    # Agent
    history_window: int = 20  # messages kept in the LLM context per conversation
    max_tool_rounds: int = 5  # tool-call rounds per turn before a final answer is forced

    @property
    def resolved_model(self) -> str:
        return self.llm_model or DEFAULT_MODELS[self.llm_provider]

    @property
    def kb_collection(self) -> str:
        """One Chroma collection per embedding model, so switching models never mixes
        vectors of different dimensions."""
        if self.kb_collection_name:
            return self.kb_collection_name
        key = f"{self.embeddings_provider}:{self.embeddings_model}"
        return "kb_" + hashlib.sha1(key.encode()).hexdigest()[:10]


@lru_cache
def get_settings() -> Settings:
    return Settings()
