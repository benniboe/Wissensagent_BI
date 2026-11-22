"""Prüft die lokale Umgebung: Python, Pakete, .env, Git-Ausschluss von .env.

Gibt keine Secret-Werte aus.  Aufruf: python scripts/check_setup.py
"""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.config import is_placeholder, load_env  # noqa: E402

PACKAGES = [
    "langgraph", "langchain_core", "langchain_openai", "langchain_text_splitters",
    "langchain_chroma", "chromadb", "langchain_huggingface", "sentence_transformers",
    "rank_bm25", "pypdf", "docx", "pydantic", "dotenv", "yaml", "streamlit",
    "pandas", "pytest", "langsmith",
]
REQUIRED_ENV = ["LITELLM_BASE_URL", "LITELLM_API_KEY", "LLM_MODEL"]


def line(ok: bool, text: str) -> bool:
    print(f"  [{'OK' if ok else '!!'}] {text}")
    return ok


def main() -> int:
    results: list[bool] = []
    print("1) Python")
    v = sys.version_info
    results.append(line((3, 11) <= (v.major, v.minor) <= (3, 12),
                        f"Python {v.major}.{v.minor}.{v.micro} (erwartet 3.11 oder 3.12)"))
    results.append(line(sys.prefix != sys.base_prefix, "virtuelle Umgebung aktiv"))

    print("2) Pakete")
    for name in PACKAGES:
        try:
            mod = importlib.import_module(name)
            results.append(line(True, f"{name} {getattr(mod, '__version__', '')}".strip()))
        except Exception as exc:  # noqa: BLE001
            results.append(line(False, f"{name} fehlt ({type(exc).__name__})"))

    print("3) .env (nur Vorhandensein, keine Werte)")
    env_file = ROOT / ".env"
    results.append(line(env_file.exists(), ".env vorhanden"))
    load_env()
    for name in REQUIRED_ENV:
        results.append(line(not is_placeholder(os.getenv(name)), f"{name} gesetzt"))

    print("4) Repository-Hygiene")
    try:
        ignored = subprocess.run(
            ["git", "check-ignore", "-q", ".env"], cwd=ROOT, check=False, stderr=subprocess.DEVNULL
        ).returncode == 0
        results.append(line(ignored, ".env wird von Git ignoriert"))
    except FileNotFoundError:
        results.append(line(False, "git nicht gefunden"))

    failed = results.count(False)
    print(f"\nErgebnis: {len(results) - failed}/{len(results)} Prüfungen OK")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
