"""Baut die Suchindizes: Korpus laden -> zerlegen -> einbetten -> Chroma + JSONL.

Die JSONL-Datei mit den Chunks ist die Grundlage für den BM25-Index.
Aufruf: python scripts/build_index.py [--config small|large]   (ohne Option: beide)
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.config import load_yaml_settings  # noqa: E402
from bi_agent.ingestion.chunking import hf_token_counter, split_documents  # noqa: E402
from bi_agent.ingestion.corpus import load_corpus  # noqa: E402
from bi_agent.retrieval.index import (  # noqa: E402
    build_dense_index, collection_name, embedding_model_name, get_embeddings, save_chunks,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=["small", "large"], default=None)
    args = parser.parse_args()

    settings = load_yaml_settings()
    corpus = "synthetic_demo"
    corpus_dir = ROOT / settings["paths"]["synthetic_corpus"] / "corpus"
    model = embedding_model_name()
    print(f"Korpus: {corpus_dir.relative_to(ROOT)} | Embedding-Modell: {model}")

    docs = load_corpus(corpus_dir)
    count = hf_token_counter(model)
    t = time.perf_counter()
    embeddings = get_embeddings(model)
    print(f"Modell geladen in {time.perf_counter() - t:.1f} s")

    for config in [args.config] if args.config else ["small", "large"]:
        name = collection_name(corpus, config)
        chunks = split_documents(docs, config, count)
        t = time.perf_counter()
        build_dense_index(chunks, name, embeddings)
        path = save_chunks(chunks, name)
        print(f"  {name}: {len(chunks)} Chunks eingebettet und gespeichert in "
              f"{time.perf_counter() - t:.1f} s -> data/index/chroma, {path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
