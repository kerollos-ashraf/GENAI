"""Shared fixtures. Tests are fully offline: hashing embeddings + a scripted fake LLM."""

import shutil
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.config import DATA_DIR, Settings
from app.infrastructure.claims_repository import JsonClaimsRepository
from app.infrastructure.embeddings import HashingEmbeddings
from app.main import create_app
from app.rag.knowledge_base import KnowledgeBase

POLICY = DATA_DIR / "policies" / "sample_policy.md"
SEED_CLAIMS = DATA_DIR / "mock_claims.seed.json"


class ScriptedLLM(GenericFakeChatModel):
    """Returns pre-scripted AIMessages (including tool calls) in order; records its inputs."""

    seen: list = []

    def bind_tools(self, tools, **kwargs):  # the real graph calls this
        return self

    def _generate(self, messages, *args, **kwargs):
        self.seen.append(messages)
        return super()._generate(messages, *args, **kwargs)


def scripted(*messages: AIMessage) -> ScriptedLLM:
    return ScriptedLLM(messages=iter(messages), seen=[])


def tool_call(name: str, args: dict) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": uuid.uuid4().hex}])


@pytest.fixture
def claims_file(tmp_path: Path) -> Path:
    path = tmp_path / "mock_claims.json"
    shutil.copy(SEED_CLAIMS, path)
    return path


@pytest.fixture
def claims_repo(claims_file: Path) -> JsonClaimsRepository:
    return JsonClaimsRepository(claims_file)


@pytest.fixture
def policies_dir(tmp_path: Path) -> Path:
    """A private copy of the policies folder, so tests can add/remove documents freely."""
    d = tmp_path / "policies"
    d.mkdir()
    shutil.copy(POLICY, d / POLICY.name)
    return d


def make_kb(docs_dir: Path, embeddings=None) -> KnowledgeBase:
    return KnowledgeBase.create(
        docs_dir, embeddings or HashingEmbeddings(), collection_name=f"t_{uuid.uuid4().hex}"
    )


@pytest.fixture
def retriever(policies_dir: Path) -> Iterator[KnowledgeBase]:
    yield make_kb(policies_dir)


@pytest.fixture
def settings(claims_file: Path, policies_dir: Path) -> Settings:
    return Settings(
        _env_file=None,
        embeddings_provider="hashing",
        chroma_dir=None,
        claims_path=claims_file,
        policies_dir=policies_dir,
        kb_watch_interval=0,
        kb_collection_name=f"t_{uuid.uuid4().hex}",
    )


@pytest.fixture
def make_client(settings: Settings) -> Iterator:
    clients = []

    def _make(llm, transcriber=None) -> TestClient:
        client = TestClient(create_app(settings, llm=llm, transcriber=transcriber))
        client.__enter__()  # runs lifespan
        clients.append(client)
        return client

    yield _make
    for c in clients:
        c.__exit__(None, None, None)
