"""Antwort aus den gefundenen Abschnitten erzeugen und Quellen deterministisch prüfen.

Wird von scripts/ask.py und vom Agenten (generate_answer, format_response) genutzt.
Nur IDs in eckigen Klammern gelten als Zitat; zitierte IDs müssen gefunden worden sein.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from html import escape

import yaml
from langchain_core.messages import HumanMessage, SystemMessage

from bi_agent.config import PROJECT_ROOT
from bi_agent.retrieval.retrievers import RetrievedChunk

DOC_ID_PATTERN = re.compile(r"\b(?:DEMO|SAN)-\d{2}\b")
# Only IDs inside square brackets count as citations: "[DEMO-03]", "[DEMO-08, DEMO-03]".
# A plain mention ("steht laut Dokument in DEMO-02") is not a citation.
CITATION_GROUP = re.compile(r"\[([^\[\]]{1,200})\]")


@lru_cache(maxsize=1)
def load_prompts() -> dict[str, str]:
    with (PROJECT_ROOT / "config" / "prompts.yaml").open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Wrap each chunk in a <document> tag: content is data, not instruction."""
    blocks = []
    for c in chunks:
        attrs = (f'id="{c.doc_id}" chunk="{c.chunk_id}" title="{escape(c.title)}" '
                 f'status="{c.status or "unknown"}"')
        # escape() stops a chunk from closing the tag and injecting its own markup
        blocks.append(f"<document {attrs}>\n{escape(c.text, quote=False)}\n</document>")
    return "\n\n".join(blocks)


@dataclass
class Answer:
    text: str
    cited_doc_ids: list[str]                 # cited AND retrieved
    invalid_citations: list[str] = field(default_factory=list)  # cited, NOT retrieved
    sources: list[dict] = field(default_factory=list)


def check_sources(answer_text: str, chunks: list[RetrievedChunk]) -> Answer:
    """Keep only citations that point to retrieved documents (criterion E4)."""
    # All retrieved chunks per document, in rank order (a document can contribute
    # several chunks; the source shows every section that was in the context).
    by_doc: dict[str, list[RetrievedChunk]] = {}
    for c in sorted(chunks, key=lambda c: c.rank):
        by_doc.setdefault(c.doc_id, []).append(c)
    cited = list(dict.fromkeys(doc_id for group in CITATION_GROUP.findall(answer_text)
                               for doc_id in DOC_ID_PATTERN.findall(group)))
    valid = [d for d in cited if d in by_doc]
    invalid = [d for d in cited if d not in by_doc]
    sources = []
    for d in valid:
        first = by_doc[d][0]
        sections = list(dict.fromkeys(c.section_heading for c in by_doc[d] if c.section_heading))
        sources.append({"doc_id": d, "title": first.title, "status": first.status,
                        "section": "; ".join(sections) or None})
    return Answer(answer_text, valid, invalid, sources)


def generate_answer(question: str, chunks: list[RetrievedChunk], llm) -> Answer:
    prompts = load_prompts()
    messages = [
        SystemMessage(prompts["answer_system"]),
        HumanMessage(prompts["answer_user"].format(context=format_context(chunks),
                                                   question=question)),
    ]
    reply = llm.invoke(messages)
    return check_sources(str(reply.content), chunks)
