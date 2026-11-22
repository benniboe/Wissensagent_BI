"""Erstellt und lädt die Suchindizes.

Dense: eine Chroma-Collection pro Korpus und Chunk-Konfiguration, Kosinus-Distanz,
Embeddings lokal (Standard BAAI/bge-m3). Die Chunks werden zusätzlich als JSONL
gespeichert; daraus baut BM25 seinen Index, so sehen alle Verfahren dieselben Chunks.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from bi_agent.config import PROJECT_ROOT, load_env, load_yaml_settings

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-m3"


def index_dir() -> Path:
    return PROJECT_ROOT / load_yaml_settings()["paths"]["index_dir"]


def collection_name(corpus: str, config_name: str) -> str:
    return f"{corpus}_{config_name}"


def embedding_model_name() -> str:
    load_env()
    return os.getenv("EMBEDDING_MODEL", "").strip() or DEFAULT_EMBEDDING_MODEL


@lru_cache(maxsize=1)
def get_embeddings(model_name: str | None = None) -> Embeddings:
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=model_name or embedding_model_name(),
        # Normalised vectors -> cosine similarity = dot product, scores in [-1, 1].
        encode_kwargs={"normalize_embeddings": True},
    )


def _chroma(name: str, embeddings: Embeddings, persist_dir: Path):
    import chromadb
    from langchain_chroma import Chroma

    return Chroma(
        collection_name=name,
        embedding_function=embeddings,
        persist_directory=str(persist_dir),
        collection_metadata={"hnsw:space": "cosine"},
        client_settings=chromadb.config.Settings(anonymized_telemetry=False),
    )


def build_dense_index(chunks: list[Document], name: str, embeddings: Embeddings,
                      persist_dir: Path | None = None):
    """(Re)build a collection from scratch so the index always matches the chunks."""
    persist_dir = persist_dir or index_dir() / "chroma"
    store = _chroma(name, embeddings, persist_dir)
    store.delete_collection()
    store = _chroma(name, embeddings, persist_dir)
    store.add_documents(chunks, ids=[c.metadata["chunk_id"] for c in chunks])
    return store


def load_dense_index(name: str, embeddings: Embeddings, persist_dir: Path | None = None):
    persist_dir = persist_dir or index_dir() / "chroma"
    store = _chroma(name, embeddings, persist_dir)
    if not store.get(limit=1)["ids"]:
        raise FileNotFoundError(
            f"Index '{name}' ist leer oder fehlt. Zuerst: python scripts/build_index.py"
        )
    return store


def chunks_path(name: str, base: Path | None = None) -> Path:
    return (base or index_dir()) / f"chunks_{name}.jsonl"


def save_chunks(chunks: list[Document], name: str, base: Path | None = None) -> Path:
    path = chunks_path(name, base)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps({"text": c.page_content, "metadata": c.metadata},
                                ensure_ascii=False) + "\n")
    return path


def load_chunks(name: str, base: Path | None = None) -> list[Document]:
    with chunks_path(name, base).open(encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    return [Document(page_content=r["text"], metadata=r["metadata"],
                     id=r["metadata"]["chunk_id"]) for r in rows]
