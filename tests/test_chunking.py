"""Loader and chunking tests. A word counter stands in for the real tokenizer
so the tests run offline and fast; the real tokenizer is used in scripts."""

import pytest

from bi_agent.config import PROJECT_ROOT
from bi_agent.ingestion.chunking import split_documents
from bi_agent.ingestion.corpus import load_corpus

CORPUS = PROJECT_ROOT / "data" / "synthetic_demo" / "corpus"


def word_count(text: str) -> int:
    return len(text.split())


@pytest.fixture(scope="module")
def docs():
    return load_corpus(CORPUS)


def test_all_formats_load_with_text_and_headings(docs):
    assert len(docs) == 9
    by_id = {d.metadata["doc_id"]: d for d in docs}
    for doc_id in ["DEMO-01", "DEMO-02", "DEMO-04"]:  # md, docx, pdf
        assert len(by_id[doc_id].text) > 1000
        assert any(m.heading for m in by_id[doc_id].markers), doc_id


def test_disclaimer_is_removed_from_text_but_kept_as_metadata(docs):
    for d in docs:
        assert "Synthetisches Beispieldokument" not in d.text
        assert d.metadata["synthetic"] is True


def test_docx_keeps_tables_in_reading_order(docs):
    demo03 = next(d for d in docs if d.metadata["doc_id"] == "DEMO-03")
    assert demo03.text.index("Tagesablauf") < demo03.text.index("PL_ERP_Orders_Daily")


@pytest.mark.parametrize("config", ["small", "large"])
def test_chunks_respect_size_and_carry_metadata(docs, config):
    chunks = split_documents(docs, config, word_count)
    limit = {"small": 400, "large": 800}[config]
    assert all(c.metadata["token_count"] <= limit for c in chunks)
    ids = [c.metadata["chunk_id"] for c in chunks]
    assert len(ids) == len(set(ids))
    for c in chunks:
        assert c.page_content.startswith(f"[{c.metadata['doc_id']} | ")
        assert c.metadata["chunking_config"] == config
        assert all(v is not None for v in c.metadata.values())


def test_small_config_produces_more_chunks_than_large(docs):
    # Word count is a lower bound for real tokens; real numbers differ, the order must not.
    small = split_documents(docs, "small", lambda t: 3 * word_count(t))
    large = split_documents(docs, "large", lambda t: 3 * word_count(t))
    assert len(small) > len(large)


def test_section_heading_is_assigned(docs):
    chunks = split_documents(docs, "small", lambda t: 3 * word_count(t))
    demo03 = [c for c in chunks if c.metadata["doc_id"] == "DEMO-03"]
    assert any("Verhalten bei Fehlern" in c.metadata.get("section_heading", "") for c in demo03)
    pdf_chunks = [c for c in chunks if c.metadata["doc_id"] == "DEMO-04"]
    assert all("page" in c.metadata for c in pdf_chunks)
