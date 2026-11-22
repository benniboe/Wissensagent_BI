"""Retrieval-Metriken auf Dokumentebene: Hit@k, Reciprocal Rank, Precision@k.

ranked_doc_ids: doc_id jedes gefundenen Chunks in Rangfolge (Duplikate möglich).
relevant: Menge der relevanten doc_ids aus der Ground Truth.
"""

from __future__ import annotations


def hit_at_k(ranked_doc_ids: list[str], relevant: set[str], k: int) -> float:
    return 1.0 if any(d in relevant for d in ranked_doc_ids[:k]) else 0.0


def reciprocal_rank(ranked_doc_ids: list[str], relevant: set[str], k: int | None = None) -> float:
    for rank, doc_id in enumerate(ranked_doc_ids[:k] if k else ranked_doc_ids, start=1):
        if doc_id in relevant:
            return 1.0 / rank
    return 0.0


def precision_at_k(ranked_doc_ids: list[str], relevant: set[str], k: int) -> float:
    top = ranked_doc_ids[:k]
    return sum(d in relevant for d in top) / k if top else 0.0
