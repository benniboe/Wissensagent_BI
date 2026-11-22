"""Reciprocal Rank Fusion (Cormack et al. 2009).

    score(d) = Summe über Listen i von  w_i / (k + rang_i(d))

Verwendet nur RÄNGE, nie die Rohscores – darum lassen sich BM25-Scores (unbeschränkt)
und Kosinus-Ähnlichkeiten überhaupt kombinieren. k = 60 dämpft den Vorteil der Spitzenränge.
"""

from __future__ import annotations


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60,
                           weights: list[float] | None = None) -> list[tuple[str, float]]:
    weights = weights or [1.0] * len(rankings)
    if len(weights) != len(rankings):
        raise ValueError("weights und rankings müssen gleich lang sein")
    scores: dict[str, float] = {}
    for ranking, w in zip(rankings, weights):
        for rank, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + w / (k + rank)
    return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
