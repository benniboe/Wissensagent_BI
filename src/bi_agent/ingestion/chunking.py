"""Token-basiertes Chunking.

Die Länge wird in Tokens des Embedding-Tokenizers gemessen, also genau so, wie das
Embedding-Modell den Text sieht. Jeder Chunk beginnt mit der Kopfzeile
"[doc_id | Titel | Abschnitt]", damit er auch allein seine Herkunft trägt.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import lru_cache

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from bi_agent.config import load_yaml_settings
from bi_agent.ingestion.corpus import SourceDocument

TokenCounter = Callable[[str], int]

# Paragraphs first, then lines (table rows), then sentences, then words.
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


@lru_cache(maxsize=2)
def hf_token_counter(model_name: str) -> TokenCounter:
    """Token counter based on the embedding model's own tokenizer."""
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    return lambda text: len(tokenizer.tokenize(text))


def chunk_config(name: str) -> tuple[int, int]:
    cfg = load_yaml_settings()["chunking"]["configs"][name]
    return cfg["chunk_size"], cfg["chunk_overlap"]


def context_header(meta: dict, heading: str | None) -> str:
    parts = [meta["doc_id"], meta["title"]]
    if heading and heading != meta["title"]:
        parts.append(heading)
    return "[" + " | ".join(parts) + "]"


def split_documents(
    documents: list[SourceDocument], config_name: str, count_tokens: TokenCounter
) -> list[Document]:
    chunk_size, chunk_overlap = chunk_config(config_name)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=count_tokens,
        separators=SEPARATORS,
    )
    chunks: list[Document] = []
    for doc in documents:
        search_from = 0
        for index, body in enumerate(splitter.split_text(doc.text)):
            # Locate the chunk in the full text to look up heading and page.
            # (Searching ourselves is more robust than the splitter's start_index,
            # which can be -1 after whitespace stripping.)
            start = doc.text.find(body, search_from)
            if start < 0:
                start = max(doc.text.find(body[:80]), 0)
            search_from = start + 1
            heading, page = doc.context_at(start)
            metadata = {
                **doc.metadata,
                "chunk_id": f"{doc.metadata['doc_id']}#{config_name}#{index:03d}",
                "chunk_index": index,
                "chunking_config": config_name,
                "token_count": count_tokens(body),
            }
            if heading:
                metadata["section_heading"] = heading
            if page:
                metadata["page"] = page
            text = f"{context_header(doc.metadata, heading)}\n{body}"
            chunks.append(Document(page_content=text, metadata=metadata, id=metadata["chunk_id"]))
    return chunks
