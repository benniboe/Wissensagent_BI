"""Sucht im Index ohne LLM und zeigt Ränge und alle Scores.

Aufruf: python scripts/search.py "Frage" [--mode dense|sparse|hybrid] [--config small|large] [-k 5]
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.agent.runtime import default_chunking_config, make_retriever  # noqa: E402
from bi_agent.config import load_yaml_settings  # noqa: E402


def fmt(value: float | None) -> str:
    return f"{value:7.3f}" if value is not None else "      –"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--config", choices=["small", "large"], default=None,
                        help="Standard: chunking.default in config/settings.yaml")
    parser.add_argument("--mode", choices=["dense", "sparse", "hybrid"], default=None,
                        help="Standard: retrieval.default_mode in config/settings.yaml")
    parser.add_argument("-k", type=int, default=5)
    args = parser.parse_args()
    config = args.config or default_chunking_config()
    mode = args.mode or load_yaml_settings()["retrieval"]["default_mode"]

    search = make_retriever(config=config, mode=mode, k=args.k)
    search("Aufwärmen")
    t = time.perf_counter()
    hits = search(args.query)
    print(f"Suche {mode}/{config} in {1000 * (time.perf_counter() - t):.0f} ms\n")
    print("Rang  Dense    BM25     RRF      Chunk                   Abschnitt")
    for h in hits:
        print(f"{h.rank:>4} {fmt(h.dense_score)} {fmt(h.bm25_score)} "
              f"{(f'{h.rrf_score:.4f}' if h.rrf_score else '     –'):>8}   "
              f"{h.chunk_id:22}  {h.section_heading or '-'}")
    print("\nBester Treffer (Anfang):\n" + hits[0].text[:400])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
