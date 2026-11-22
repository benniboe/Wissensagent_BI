"""BM25 (Stichwortsuche) mit eigener, sichtbarer Tokenisierung.

- Kleinschreibung, Umlaute bleiben erhalten
- technische Namen bleiben EIN Token und werden zusätzlich zerlegt:
  "PL_ERP_Orders_Daily" -> pl_erp_orders_daily, pl, erp, orders, daily
- kleine Stoppwortliste Deutsch/Englisch, kein Stemming
  (Grenze: "Refresh" und "Refreshfehler" passen nicht zusammen)
"""

from __future__ import annotations

import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from bi_agent.retrieval.retrievers import RetrievedChunk, _to_chunk

TOKEN = re.compile(r"[a-zäöüß0-9]+(?:[_\-.][a-zäöüß0-9]+)*")
STOPWORDS = set("""
der die das den dem des ein eine einer eines einem einen und oder aber nicht
ist sind wird werden wurde wie was wer wo wann warum welche welcher welches
mit von zu zum zur im in am an auf aus bei für fuer ob als auch noch nur so
es er sie wir ich man dass da den diese dieser dieses
the a an and or of to in on for is are be what how who when which with
""".split())


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    for tok in TOKEN.findall(text.lower()):
        if tok in STOPWORDS:
            continue
        tokens.append(tok)
        parts = re.split(r"[_\-.]", tok)
        if len(parts) > 1:
            tokens.extend(p for p in parts if p and p not in STOPWORDS)
    return tokens


class BM25Index:
    def __init__(self, chunks: list[Document]):
        if not chunks:
            raise ValueError("BM25Index braucht mindestens einen Chunk")
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokenize(c.page_content) for c in chunks])

    def search(self, query: str, k: int) -> list[RetrievedChunk]:
        scores = self.bm25.get_scores(tokenize(query))
        order = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [_to_chunk(self.chunks[i], rank, bm25_score=round(float(scores[i]), 4))
                for rank, i in enumerate(order, start=1)]
