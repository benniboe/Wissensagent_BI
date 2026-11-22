"""Zentrale Konfiguration: Secrets aus der Umgebung (.env), Parameter aus config/*.yaml."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLACEHOLDER_PREFIXES = ("<PLATZHALTER", "<OPTIONAL")


class ConfigError(RuntimeError):
    """Raised when a required setting is missing or still a placeholder."""


def is_placeholder(value: str | None) -> bool:
    return not value or value.strip().startswith(PLACEHOLDER_PREFIXES)


class LLMSettings(BaseModel):
    base_url: str
    api_key: str = Field(repr=False)  # never printed
    model: str
    classifier_model: str
    temperature: float | None = None  # None = not sent, model default applies
    timeout_seconds: float = 60.0


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if is_placeholder(value):
        raise ConfigError(
            f"Umgebungsvariable {name} fehlt oder ist noch ein Platzhalter. "
            f"Bitte in .env eintragen (Vorlage: .env.example)."
        )
    return value.strip()


def _optional_float(name: str) -> float | None:
    value = os.getenv(name, "").strip()
    return float(value) if value else None


def load_env(env_file: Path | None = None) -> None:
    """Load .env from the project root; existing environment variables win."""
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)


def get_llm_settings() -> LLMSettings:
    load_env()
    model = _required_env("LLM_MODEL")
    classifier = os.getenv("LLM_MODEL_CLASSIFIER", "").strip() or model
    return LLMSettings(
        base_url=_required_env("LITELLM_BASE_URL"),
        api_key=_required_env("LITELLM_API_KEY"),
        model=model,
        classifier_model=classifier,
        temperature=_optional_float("LLM_TEMPERATURE"),
        timeout_seconds=float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
    )


@lru_cache(maxsize=1)
def load_yaml_settings(path: str | None = None) -> dict[str, Any]:
    settings_path = Path(path) if path else PROJECT_ROOT / "config" / "settings.yaml"
    with settings_path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)
