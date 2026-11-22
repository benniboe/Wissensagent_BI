"""Einfache RAG-Kette ohne Agent: suchen -> antworten -> Quellen prüfen.

Zum Vergleich mit dem Agenten (keine Guardrails, keine Einordnung, kein Evidenz-Check).
Aufruf: python scripts/ask.py "Frage" [--config small] [-k 5]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.answering import generate_answer  # noqa: E402
from bi_agent.llm.litellm_client import get_chat_model  # noqa: E402
from bi_agent.agent.runtime import default_chunking_config  # noqa: E402
from bi_agent.retrieval.index import collection_name, get_embeddings, load_dense_index  # noqa: E402
from bi_agent.retrieval.retrievers import dense_search  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--config", choices=["small", "large"], default=None,
                        help="Standard: chunking.default in config/settings.yaml")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    args.config = args.config or default_chunking_config()

    store = load_dense_index(collection_name("synthetic_demo", args.config), get_embeddings())
    t0 = time.perf_counter()
    chunks = dense_search(store, args.question, args.k)
    t1 = time.perf_counter()
    answer = generate_answer(args.question, chunks, get_chat_model())
    t2 = time.perf_counter()

    print("ANTWORT\n" + answer.text)
    print("\nQUELLEN (geprüft: zitiert UND gefunden)")
    for s in answer.sources:
        note = "" if s["status"] == "current" else f"  <- Status: {s['status']}"
        print(f"  {s['doc_id']}  {s['title']}  ({s['section'] or '-'}){note}")
    if not answer.sources:
        print("  keine")
    if answer.invalid_citations:
        print(f"\nWARNUNG: zitiert, aber nicht gefunden: {answer.invalid_citations}")
    print(f"\nGEFUNDENE CHUNKS: " + ", ".join(f"{c.chunk_id} ({c.dense_score:.2f})" for c in chunks))
    print(f"Zeit: Suche {1000 * (t1 - t0):.0f} ms, Antwort {t2 - t1:.1f} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
