"""Chat-model factory (Factory + Registry).

Each provider registers a builder with `@register_provider`. Adding a provider means adding
one decorated function - `create_llm` itself never changes (Open/Closed).
"""

import os
from collections.abc import Callable
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel

from app.config import Settings
from app.domain.errors import ServiceUnavailableError

LLMBuilder = Callable[[Settings], BaseChatModel]


class LLMNotConfiguredError(ServiceUnavailableError):
    pass


@dataclass(frozen=True)
class _Provider:
    build: LLMBuilder
    api_key_env: str | None


_PROVIDERS: dict[str, _Provider] = {}


def register_provider(name: str, api_key_env: str | None = None):
    def decorator(build: LLMBuilder) -> LLMBuilder:
        _PROVIDERS[name] = _Provider(build, api_key_env)
        return build

    return decorator


def check_api_key(provider: str) -> None:
    """Fail fast with a clear message: an empty key otherwise surfaces as a vague
    'connection error' on the first chat request."""
    entry = _PROVIDERS.get(provider)
    env = entry.api_key_env if entry else None
    if env and not os.environ.get(env, "").strip():
        raise LLMNotConfiguredError(
            f"{env} is not set. Add it to the .env file in the project root and restart "
            f"(or set LLM_PROVIDER=ollama to use a local model)."
        )


def sampling_kwargs(settings: Settings) -> dict:
    """Send `temperature` only when explicitly configured. Many newer models (OpenAI's
    reasoning models, for example) reject it with HTTP 400, so the provider default is the
    only setting that works with every model."""
    if settings.llm_temperature is None:
        return {}
    return {"temperature": settings.llm_temperature}


def create_llm(settings: Settings) -> BaseChatModel:
    provider = _PROVIDERS.get(settings.llm_provider)
    if provider is None:
        raise LLMNotConfiguredError(f"Unknown LLM provider '{settings.llm_provider}'")
    check_api_key(settings.llm_provider)
    try:
        return provider.build(settings)
    except Exception as exc:  # pragma: no cover - bad model name, missing package, ...
        raise LLMNotConfiguredError(
            f"Could not initialise LLM provider '{settings.llm_provider}': {exc}"
        ) from exc


# --- Providers (imports are lazy so unused SDKs are never loaded) --------------------------


@register_provider("groq", api_key_env="GROQ_API_KEY")
def _groq(settings: Settings) -> BaseChatModel:  # pragma: no cover
    from langchain_groq import ChatGroq

    return ChatGroq(model=settings.resolved_model, **sampling_kwargs(settings))


@register_provider("openai", api_key_env="OPENAI_API_KEY")
def _openai(settings: Settings) -> BaseChatModel:  # pragma: no cover
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(model=settings.resolved_model, **sampling_kwargs(settings))


@register_provider("anthropic", api_key_env="ANTHROPIC_API_KEY")
def _anthropic(settings: Settings) -> BaseChatModel:  # pragma: no cover
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(model=settings.resolved_model, **sampling_kwargs(settings))


@register_provider("ollama")
def _ollama(settings: Settings) -> BaseChatModel:  # pragma: no cover
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=settings.resolved_model,
        base_url=settings.ollama_base_url,
        **sampling_kwargs(settings),
    )
