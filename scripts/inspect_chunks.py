"""Zeigt, wie der Korpus in Chunks zerlegt wird.

  python scripts/inspect_chunks.py                 # Statistik für beide Konfigurationen
  python scripts/inspect_chunks.py --show DEMO-03  # alle Chunks eines Dokuments
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.config import load_env, load_yaml_settings  # noqa: E402
from bi_agent.ingestion.chunking import hf_token_counter, split_documents  # noqa: E402
from bi_agent.ingestion.corpus import load_corpus  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=["small", "large"], default=None)
    parser.add_argument("--show", metavar="DOC_ID", help="alle Chunks eines Dokuments anzeigen")
    args = parser.parse_args()

    load_env()
    settings = load_yaml_settings()
    model = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    count = hf_token_counter(model)
    docs = load_corpus(ROOT / settings["paths"]["synthetic_corpus"] / "corpus")

    print(f"Tokenizer: {model}")
    print(f"{len(docs)} Dokumente geladen")
    for d in docs:
        print(f"  {d.metadata['doc_id']}: {count(d.text):5d} Tokens, "
              f"{sum(1 for m in d.markers if m.heading)} Überschriften")

    for name in [args.config] if args.config else ["small", "large"]:
        chunks = split_documents(docs, name, count)
        sizes = [c.metadata["token_count"] for c in chunks]
        print(f"\nKonfiguration {name}: {len(chunks)} Chunks, "
              f"Tokens Ø {mean(sizes):.0f}, min {min(sizes)}, max {max(sizes)}")
        if args.show:
            for c in chunks:
                if c.metadata["doc_id"] == args.show:
                    print(f"\n--- {c.metadata['chunk_id']} ({c.metadata['token_count']} Tokens, "
                          f"Abschnitt: {c.metadata.get('section_heading', '-')}, "
                          f"Seite: {c.metadata.get('page', '-')})")
                    print(c.page_content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
