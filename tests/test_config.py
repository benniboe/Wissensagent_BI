"""Configuration tests – no network access, no real secrets."""

import pytest

from bi_agent.config import ConfigError, get_llm_settings, is_placeholder, load_yaml_settings
from bi_agent.llm.litellm_client import get_chat_model


def test_placeholders_are_detected():
    assert is_placeholder("<PLATZHALTER_PERSOENLICHER_KEY>")
    assert is_placeholder("")
    assert is_placeholder(None)
    assert not is_placeholder("gpt-test")


def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "<PLATZHALTER_PERSOENLICHER_KEY>")
    monkeypatch.setenv("LLM_MODEL", "some-model")
    with pytest.raises(ConfigError, match="LITELLM_API_KEY"):
        get_llm_settings()


def test_chat_model_uses_env_and_hides_key(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test-not-real-1234567890")
    monkeypatch.setenv("LLM_MODEL", "answer-model")
    monkeypatch.setenv("LLM_MODEL_CLASSIFIER", "small-model")
    settings = get_llm_settings()
    assert "sk-test" not in repr(settings)  # key is excluded from repr
    assert get_chat_model(settings=settings).model_name == "answer-model"
    assert get_chat_model("classifier", settings=settings).model_name == "small-model"


def test_yaml_settings_have_both_chunking_configs():
    cfg = load_yaml_settings()
    assert set(cfg["chunking"]["configs"]) == {"small", "large"}
    assert cfg["retrieval"]["rrf_k"] == 60


def test_empty_temperature_is_not_sent(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "https://example.invalid/v1")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test-not-real-1234567890")
    monkeypatch.setenv("LLM_MODEL", "answer-model")
    monkeypatch.setenv("LLM_TEMPERATURE", "")
    settings = get_llm_settings()
    assert settings.temperature is None
    assert get_chat_model(settings=settings).temperature is None
