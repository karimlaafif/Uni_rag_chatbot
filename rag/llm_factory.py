"""
rag/llm_factory.py — LLM Abstraction Layer
===========================================
Single entry point for constructing any supported LLM backend.
Swap providers by changing LLM_PROVIDER in .env — zero code changes.

Supported providers:
  - ollama     : Local inference via Ollama (default, free, private)
  - openai     : OpenAI API (best quality, paid)
  - anthropic  : Anthropic Claude API

Usage:
    from rag.llm_factory import build_llm

    llm = build_llm()              # uses settings.LLM_PROVIDER
    llm = build_llm("openai")      # explicit override
    llm = build_llm("ollama", model="phi3")  # explicit model
"""

import logging
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


def build_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
):
    """
    Build and return a LangChain-compatible chat LLM.

    Parameters
    ----------
    provider    : LLM backend. Defaults to settings.LLM_PROVIDER.
    model       : Model identifier. Falls back to provider defaults.
    temperature : Sampling temperature (0 = deterministic).

    Returns
    -------
    A LangChain BaseChatModel instance.
    """
    provider = provider or settings.LLM_PROVIDER

    # ── Ollama (local) ───────────────────────────────────────────────────────
    if provider == "ollama":
        from langchain_community.chat_models import ChatOllama

        resolved_model = model or settings.OLLAMA_MODEL
        logger.info(f"[LLMFactory] Using Ollama — model={resolved_model}")

        return ChatOllama(
            model=resolved_model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=temperature,
        )

    # ── OpenAI ──────────────────────────────────────────────────────────────
    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.OPENAI_API_KEY:
            raise EnvironmentError(
                "OPENAI_API_KEY is not set. Add it to your .env file."
            )

        resolved_model = model or getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
        logger.info(f"[LLMFactory] Using OpenAI — model={resolved_model}")

        return ChatOpenAI(
            model=resolved_model,
            temperature=temperature,
            api_key=settings.OPENAI_API_KEY,
        )

    # ── Anthropic ────────────────────────────────────────────────────────────
    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not settings.ANTHROPIC_API_KEY:
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file."
            )

        resolved_model = model or "claude-3-haiku-20240307"
        logger.info(f"[LLMFactory] Using Anthropic — model={resolved_model}")

        return ChatAnthropic(
            model=resolved_model,
            temperature=temperature,
            api_key=settings.ANTHROPIC_API_KEY,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider '{provider}'. "
            "Valid options: ollama | openai | anthropic"
        )


def list_available_providers() -> dict:
    """
    Returns a dict describing which providers are configured and available.
    Useful for health-check endpoints and debugging.
    """
    return {
        "ollama": {
            "available": True,  # always available if Ollama is running
            "base_url": settings.OLLAMA_BASE_URL,
            "default_model": settings.OLLAMA_MODEL,
        },
        "openai": {
            "available": bool(settings.OPENAI_API_KEY),
            "key_set": bool(settings.OPENAI_API_KEY),
        },
        "anthropic": {
            "available": bool(settings.ANTHROPIC_API_KEY),
            "key_set": bool(settings.ANTHROPIC_API_KEY),
        },
        "active_provider": settings.LLM_PROVIDER,
    }
