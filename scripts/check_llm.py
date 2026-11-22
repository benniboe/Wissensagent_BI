"""Verbindungstest zum FHNW-LiteLLM-Proxy.

  python scripts/check_llm.py --list   # Modelle, die der eigene Schlüssel sieht
  python scripts/check_llm.py          # ein kurzer Testaufruf mit LLM_MODEL
Sendet nur einen festen Testsatz, keine Korpusinhalte.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.config import ConfigError, get_llm_settings, load_env  # noqa: E402


def hint_for(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    if "401" in text or "Authentication" in text:
        return "Schlüssel ungültig/abgelaufen -> LITELLM_API_KEY prüfen."
    if "404" in text or "NotFound" in text:
        return ("Endpunkt oder Modell nicht gefunden -> LITELLM_BASE_URL (mit/ohne /v1?) "
                "und LLM_MODEL mit --list vergleichen.")
    if "Connect" in text or "Timeout" in text:
        return "Keine Verbindung -> VPN/Netz, Base-URL und Tippfehler prüfen."
    if "429" in text or "Budget" in text or "budget" in text:
        return "Rate-Limit oder Kostenlimit erreicht -> kurz warten, Budget in LiteLLM prüfen."
    return "Unerwarteter Fehler – vollständige Meldung oben lesen."


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true", help="Modelle auflisten")
    args = parser.parse_args()

    load_env()
    try:
        if args.list:
            # Listing works without LLM_MODEL being set yet.
            import os

            from openai import OpenAI

            base_url, api_key = os.getenv("LITELLM_BASE_URL"), os.getenv("LITELLM_API_KEY")
            if not base_url or not api_key or base_url.startswith("<") or api_key.startswith("<"):
                raise ConfigError("LITELLM_BASE_URL und LITELLM_API_KEY in .env setzen.")
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=30)
            names = sorted(m.id for m in client.models.list())
            print(f"{len(names)} Modelle verfügbar:")
            for n in names:
                print(" -", n)
            return 0

        from bi_agent.llm.litellm_client import get_chat_model

        settings = get_llm_settings()
        print(f"Base-URL: {settings.base_url}")
        print(f"Modell:   {settings.model}")
        llm = get_chat_model(settings=settings)
        start = time.perf_counter()
        reply = llm.invoke("Antworte nur mit dem Wort OK.")
        elapsed = time.perf_counter() - start
        print(f"Antwort:  {reply.content!r}")
        print(f"Latenz:   {elapsed:.2f} s")
        usage = getattr(reply, "usage_metadata", None)
        if usage:
            print(f"Tokens:   {usage}")
        print("Verbindung OK.")
        return 0
    except ConfigError as exc:
        print(f"Konfiguration unvollständig: {exc}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"Fehler: {type(exc).__name__}: {exc}")
        print(f"Hinweis: {hint_for(exc)}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
