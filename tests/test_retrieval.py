"""Index, dense search and metrics – offline with fake embeddings."""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from bi_agent.config import PROJECT_ROOT
from bi_agent.evaluation.metrics import hit_at_k, precision_at_k, reciprocal_rank
from bi_agent.ingestion.chunking import split_documents
from bi_agent.ingestion.corpus import load_corpus
from bi_agent.retrieval.index import build_dense_index, load_chunks, load_dense_index, save_chunks
from bi_agent.retrieval.retrievers import dense_search


@pytest.fixture(scope="module")
def chunks():
    docs = load_corpus(PROJECT_ROOT / "data" / "synthetic_demo" / "corpus")
    return split_documents(docs, "small", lambda t: 2 * len(t.split()))


@pytest.fixture()
def store(chunks, tmp_path):
    return build_dense_index(chunks, "test_small", DeterministicFakeEmbedding(size=32), tmp_path)


def test_index_holds_every_chunk_once(store, chunks):
    assert len(store.get()["ids"]) == len(chunks)


def test_rebuild_replaces_instead_of_duplicating(chunks, tmp_path):
    emb = DeterministicFakeEmbedding(size=32)
    build_dense_index(chunks, "test_small", emb, tmp_path)
    store = build_dense_index(chunks, "test_small", emb, tmp_path)
    assert len(store.get()["ids"]) == len(chunks)


def test_identical_text_is_rank_one_with_similarity_near_one(store, chunks):
    target = chunks[3]
    hits = dense_search(store, target.page_content, k=5)
    assert [h.rank for h in hits] == [1, 2, 3, 4, 5]
    assert hits[0].chunk_id == target.metadata["chunk_id"]
    assert hits[0].dense_score > 0.99
    assert hits[0].dense_score >= hits[1].dense_score


def test_missing_index_gives_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="build_index"):
        load_dense_index("does_not_exist", DeterministicFakeEmbedding(size=32), tmp_path)


def test_chunks_roundtrip_jsonl(chunks, tmp_path):
    save_chunks(chunks, "x", tmp_path)
    loaded = load_chunks("x", tmp_path)
    assert [c.metadata["chunk_id"] for c in loaded] == [c.metadata["chunk_id"] for c in chunks]


def test_metrics_on_known_ranking():
    ranked = ["DEMO-02", "DEMO-01", "DEMO-01", "DEMO-05", "DEMO-03"]
    relevant = {"DEMO-01"}
    assert hit_at_k(ranked, relevant, 1) == 0.0
    assert hit_at_k(ranked, relevant, 3) == 1.0
    assert reciprocal_rank(ranked, relevant) == 0.5
    assert precision_at_k(ranked, relevant, 5) == 0.4
    assert reciprocal_rank(ranked, {"DEMO-09"}) == 0.0
