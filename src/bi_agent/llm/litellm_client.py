"""Anbindung an den FHNW-LiteLLM-Proxy.

LiteLLM ist OpenAI-kompatibel, deshalb zeigt ChatOpenAI per base_url auf den Proxy.
Modellwechsel = LLM_MODEL in .env ändern. Temperatur wird nur gesendet, wenn gesetzt.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from bi_agent.config import LLMSettings, get_llm_settings


def get_chat_model(
    purpose: str = "answer", settings: LLMSettings | None = None
) -> ChatOpenAI:
    """Return a chat model. purpose='classifier' may use a cheaper model."""
    s = settings or get_llm_settings()
    model = s.classifier_model if purpose == "classifier" else s.model
    kwargs = {}
    if s.temperature is not None:  # some models (e.g. Claude Haiku 5.5) accept only their default
        kwargs["temperature"] = s.temperature
    return ChatOpenAI(
        model=model,
        base_url=s.base_url,
        api_key=s.api_key,
        timeout=s.timeout_seconds,
        max_retries=2,
        **kwargs,
    )
