"""Suchverfahren Dense und Hybrid.

Alle Verfahren liefern dieselbe Form (Liste von RetrievedChunk in Rangfolge),
damit Agent und Evaluation nicht wissen müssen, welches Verfahren gesucht hat.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from langchain_core.documents import Document


@dataclass
class RetrievedChunk:
    rank: int                       # 1 = best
    chunk_id: str
    doc_id: str
    title: str
    section_heading: str | None
    text: str
    dense_score: float | None = None   # cosine similarity, higher = more similar
    bm25_score: float | None = None    # nur bei BM25 bzw. Hybrid
    rrf_score: float | None = None     # nur bei BM25 bzw. Hybrid
    status: str | None = None          # current | outdated | draft (for conflicts)

    def to_dict(self) -> dict:
        return asdict(self)


def _to_chunk(doc: Document, rank: int, **scores) -> RetrievedChunk:
    m = doc.metadata
    return RetrievedChunk(rank=rank, chunk_id=m["chunk_id"], doc_id=m["doc_id"],
                          title=m["title"], section_heading=m.get("section_heading"),
                          text=doc.page_content, status=m.get("status"), **scores)


def dense_search(store, query: str, k: int) -> list[RetrievedChunk]:
    """Chroma returns cosine DISTANCE (0 = identical); we report similarity = 1 - distance."""
    hits = store.similarity_search_with_score(query, k=k)
    return [_to_chunk(doc, rank, dense_score=round(1.0 - distance, 4))
            for rank, (doc, distance) in enumerate(hits, start=1)]


def hybrid_search(store, bm25, query: str, k: int, candidate_k: int = 20,
                  rrf_k: int = 60, weights: list[float] | None = None) -> list[RetrievedChunk]:
    """Dense + BM25, each with `candidate_k` candidates, fused with RRF.

    Every returned chunk keeps the scores of both lists (None if absent), so the
    evidence check can still use the dense similarity and the UI can show why a
    chunk was found.
    """
    from bi_agent.retrieval.fusion import reciprocal_rank_fusion

    dense = dense_search(store, query, candidate_k)
    sparse = bm25.search(query, candidate_k)
    by_id = {c.chunk_id: c for c in sparse} | {c.chunk_id: c for c in dense}
    dense_scores = {c.chunk_id: c.dense_score for c in dense}
    bm25_scores = {c.chunk_id: c.bm25_score for c in sparse}
    fused = reciprocal_rank_fusion([[c.chunk_id for c in dense], [c.chunk_id for c in sparse]],
                                   k=rrf_k, weights=weights)
    out = []
    for rank, (chunk_id, score) in enumerate(fused[:k], start=1):
        base = by_id[chunk_id]
        out.append(RetrievedChunk(
            rank=rank, chunk_id=chunk_id, doc_id=base.doc_id, title=base.title,
            section_heading=base.section_heading, text=base.text, status=base.status,
            dense_score=dense_scores.get(chunk_id), bm25_score=bm25_scores.get(chunk_id),
            rrf_score=round(score, 5)))
    return out
