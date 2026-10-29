"""FastAPI entry point: builds the container at startup and mounts the routers. No business
logic lives here."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.language_models import BaseChatModel

from app.api.errors import register_error_handlers
from app.api.routes import chat, documents, voice
from app.config import Settings, get_settings
from app.container import Container
from app.domain.ports import Transcriber

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def create_app(
    settings: Settings | None = None,
    llm: BaseChatModel | None = None,
    transcriber: Transcriber | None = None,
) -> FastAPI:
    """App factory. `llm` and `transcriber` are overridable so tests run fully offline."""
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = Container.build(settings, llm=llm, transcriber=transcriber)
        container.start()
        app.state.container = container
        yield
        container.stop()

    app = FastAPI(
        title="OmniCare Assistant API",
        version="1.0.0",
        description="Policy Q&A (RAG with citations) + claim tools, orchestrated with LangGraph.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    for router in (chat.router, documents.router, voice.router):
        app.include_router(router)
    return app


app = create_app()
