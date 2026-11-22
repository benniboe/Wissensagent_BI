"""Baut den Agenten mit den echten Komponenten (LiteLLM, lokale Embeddings, Chroma, BM25).

    agent = build_agent()
    state = ask(agent, "Welche Reports nutzen das Modell Verkauf?", thread_id="demo-1")
"""

from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver

from bi_agent.agent.graph import build_graph
from bi_agent.agent.nodes import Dependencies
from bi_agent.agent.schemas import EvidenceAssessment, QueryClassification
from bi_agent.answering import format_context, load_prompts
from bi_agent.config import PROJECT_ROOT, load_yaml_settings
from bi_agent.llm.litellm_client import get_chat_model
from bi_agent.retrieval.index import collection_name, get_embeddings, load_chunks, load_dense_index
from bi_agent.retrieval.retrievers import RetrievedChunk, dense_search, hybrid_search
from bi_agent.retrieval.sparse import BM25Index


def default_chunking_config() -> str:
    return load_yaml_settings()["chunking"]["default"]


def make_retriever(corpus: str = "synthetic_demo", config: str | None = None,
                   mode: str | None = None, k: int | None = None):
    settings = load_yaml_settings()
    config = config or default_chunking_config()
    mode = mode or settings["retrieval"]["default_mode"]
    k = k or settings["retrieval"]["top_k"]
    name = collection_name(corpus, config)
    if mode == "sparse":
        bm25 = BM25Index(load_chunks(name))
        return lambda query: bm25.search(query, k)
    store = load_dense_index(name, get_embeddings())
    if mode == "dense":
        return lambda query: dense_search(store, query, k)
    if mode == "hybrid":
        bm25 = BM25Index(load_chunks(name))
        r = settings["retrieval"]
        return lambda query: hybrid_search(store, bm25, query, k, r["candidate_k"], r["rrf_k"])
    raise ValueError(f"Unbekannter Retrieval-Modus: {mode}")


def build_dependencies(retrieve=None) -> Dependencies:
    settings = load_yaml_settings()
    agent_cfg = settings["agent"]
    prompts = load_prompts()
    method = agent_cfg.get("structured_output_method", "json_schema")
    classifier = get_chat_model("classifier").with_structured_output(QueryClassification, method=method)
    assessor = get_chat_model("classifier").with_structured_output(EvidenceAssessment, method=method)

    def classify(history: str, question: str) -> QueryClassification:
        return classifier.invoke([
            SystemMessage(prompts["classify_system"]),
            HumanMessage(prompts["classify_user"].format(history=history, question=question)),
        ])

    def assess(question: str, chunks: list[RetrievedChunk]) -> EvidenceAssessment:
        return assessor.invoke([
            SystemMessage(prompts["evidence_system"]),
            HumanMessage(prompts["evidence_user"].format(question=question,
                                                         context=format_context(chunks))),
        ])

    return Dependencies(
        classify=classify, assess=assess, retrieve=retrieve or make_retriever(),
        answer_llm=get_chat_model("answer"),
        min_dense_similarity=float(settings["retrieval"]["min_dense_similarity"]),
        max_history_messages=agent_cfg["max_history_messages"],
        max_query_chars=agent_cfg["max_query_chars"],
        escalation_contact=agent_cfg.get("escalation_contact", "BI-Fachrolle"),
        logs_dir=PROJECT_ROOT / agent_cfg.get("logs_dir", "logs"),
    )


def build_agent(deps: Dependencies | None = None, checkpointer=None):
    """Compiled graph with short-term memory (InMemorySaver, SW8)."""
    return build_graph(deps or build_dependencies(), checkpointer or InMemorySaver())


def ask(agent, question: str, thread_id: str) -> dict:
    config = {"configurable": {"thread_id": thread_id}}
    return agent.invoke({"messages": [HumanMessage(content=question)]}, config)
