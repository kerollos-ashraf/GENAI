"""Composition root: the ONE place where concrete classes are chosen and wired together.

Everything else receives its collaborators through constructors (Dependency Injection), so
tests swap any piece - the LLM, the transcriber - by passing an override here.
"""

import logging
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel

from app.agent.response import TurnFormatter
from app.agent.tools import AssistantToolkit
from app.agent.workflow import AssistantWorkflow
from app.config import Settings
from app.domain.errors import ServiceUnavailableError
from app.domain.ports import ChatAssistant, InputGuard, Transcriber
from app.infrastructure.claims_repository import JsonClaimsRepository
from app.infrastructure.embeddings import create_embeddings
from app.infrastructure.llm import create_llm
from app.infrastructure.speech import GroqWhisperTranscriber
from app.rag.knowledge_base import KnowledgeBase
from app.rag.watcher import FolderWatcher
from app.security.guard import PatternInjectionGuard
from app.services.chat_service import ChatService, UnavailableChatService
from app.services.document_service import DocumentService
from app.services.voice_service import VoiceService

logger = logging.getLogger(__name__)


@dataclass
class Container:
    settings: Settings
    knowledge_base: KnowledgeBase
    chat: ChatAssistant
    documents: DocumentService
    voice: VoiceService
    watcher: FolderWatcher

    @classmethod
    def build(
        cls,
        settings: Settings,
        llm: BaseChatModel | None = None,
        transcriber: Transcriber | None = None,
    ) -> "Container":
        guard = PatternInjectionGuard()

        profile = create_embeddings(settings)
        knowledge_base = KnowledgeBase.create(
            settings.policies_dir,
            profile.embeddings,
            collection_name=profile.collection_name,
            persist_dir=settings.chroma_dir,
            guard=guard,  # screens every document, including files dropped in the folder
        )
        watcher = FolderWatcher(
            signature=knowledge_base.store.signature,
            on_change=knowledge_base.sync,
            interval=settings.kb_watch_interval,
        )

        toolkit = AssistantToolkit(
            knowledge_base, JsonClaimsRepository(settings.claims_path), settings.rag_top_k
        )
        chat = cls._build_chat(settings, llm, toolkit, guard)

        return cls(
            settings=settings,
            knowledge_base=knowledge_base,
            chat=chat,
            documents=DocumentService(knowledge_base, guard, settings.max_document_bytes),
            voice=VoiceService(
                transcriber or GroqWhisperTranscriber(settings.stt_model),
                chat,
                settings.max_audio_bytes,
            ),
            watcher=watcher,
        )

    @staticmethod
    def _build_chat(
        settings: Settings,
        llm: BaseChatModel | None,
        toolkit: AssistantToolkit,
        guard: InputGuard,
    ) -> ChatAssistant:
        try:
            model = llm or create_llm(settings)
        except ServiceUnavailableError as exc:
            logger.error("%s", exc)
            return UnavailableChatService(str(exc))
        workflow = AssistantWorkflow(
            model,
            toolkit.tools(),
            guard,
            history_window=settings.history_window,
            max_tool_rounds=settings.max_tool_rounds,
        )
        logger.info(
            "Agent ready (provider=%s, model=%s)", settings.llm_provider, settings.resolved_model
        )
        return ChatService(workflow, TurnFormatter())

    def start(self) -> None:
        self.watcher.start()

    def stop(self) -> None:
        self.watcher.stop()
