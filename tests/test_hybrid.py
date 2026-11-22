"""BM25 tokenisation, RRF arithmetic (SW7 slide example) and hybrid search."""

import pytest
from langchain_core.embeddings import DeterministicFakeEmbedding

from bi_agent.config import PROJECT_ROOT
from bi_agent.ingestion.chunking import split_documents
from bi_agent.ingestion.corpus import load_corpus
from bi_agent.retrieval.fusion import reciprocal_rank_fusion
from bi_agent.retrieval.index import build_dense_index
from bi_agent.retrieval.retrievers import hybrid_search
from bi_agent.retrieval.sparse import BM25Index, tokenize


@pytest.fixture(scope="module")
def chunks():
    docs = load_corpus(PROJECT_ROOT / "data" / "synthetic_demo" / "corpus")
    return split_documents(docs, "small", lambda t: 2 * len(t.split()))


def test_tokenizer_keeps_technical_names_and_their_parts():
    tokens = tokenize("Was passiert, wenn PL_ERP_Orders_Daily fehlschlägt?")
    assert "pl_erp_orders_daily" in tokens and "erp" in tokens and "daily" in tokens
    assert "was" not in tokens                               # stop word removed
    assert "fehlschlägt" in tokens                          # umlauts kept


def test_rrf_reproduces_slide_example():
    # SW7: A sparse 1 / dense 3, B sparse 2 / dense 1, C sparse 3 / dense 2 -> B > A > C
    fused = reciprocal_rank_fusion([["A", "B", "C"], ["B", "C", "A"]], k=60, weights=[0.5, 0.5])
    assert [d for d, _ in fused] == ["B", "A", "C"]
    assert round(fused[0][1], 4) == round(0.5 / 62 + 0.5 / 61, 4)


def test_rrf_document_in_one_list_only_gets_one_share():
    fused = dict(reciprocal_rank_fusion([["A"], ["B"]], k=60))
    assert fused["A"] == fused["B"] == pytest.approx(1 / 61)


def test_bm25_finds_exact_pipeline_name(chunks):
    hits = BM25Index(chunks).search("PL_PPS_Production_Daily Start", 3)
    assert hits[0].doc_id in {"DEMO-02", "DEMO-03"}
    assert hits[0].bm25_score > 0 and hits[0].dense_score is None


def test_hybrid_combines_both_lists_and_keeps_scores(chunks, tmp_path):
    store = build_dense_index(chunks, "test_hybrid", DeterministicFakeEmbedding(size=32), tmp_path)
    hits = hybrid_search(store, BM25Index(chunks), "PL_PPS_Production_Daily", k=5)
    assert [h.rank for h in hits] == [1, 2, 3, 4, 5]
    assert all(h.rrf_score for h in hits)
    assert hits[0].rrf_score >= hits[-1].rrf_score
    assert any(h.dense_score is not None for h in hits)
    assert any(h.bm25_score is not None for h in hits)
