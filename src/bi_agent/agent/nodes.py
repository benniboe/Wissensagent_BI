"""Die Nodes des Graphen: Zustand rein, Zustandsänderung raus.

LLMs und Retriever werden über `Dependencies` übergeben. So lässt sich der ganze
Graph in den Tests mit Fakes prüfen – ohne Netzwerk und deterministisch.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage

from bi_agent.agent.guardrails import REFUSAL_TEXTS, check_input, normalize_text, redact_output
from bi_agent.agent.schemas import EvidenceAssessment, QueryClassification
from bi_agent.agent.state import PER_TURN_RESET, AgentState
from bi_agent.answering import generate_answer as llm_generate_answer
from bi_agent.retrieval.retrievers import RetrievedChunk
from bi_agent.utils.logging import log_gap, log_turn


@dataclass
class Dependencies:
    classify: Callable[[str, str], QueryClassification]          # (history, question)
    assess: Callable[[str, list[RetrievedChunk]], EvidenceAssessment]
    retrieve: Callable[[str], list[RetrievedChunk]]
    answer_llm: object                                            # LangChain chat model
    min_dense_similarity: float = 0.35
    max_history_messages: int = 10
    max_query_chars: int = 2000
    escalation_contact: str = "BI-Fachrolle"
    logs_dir: Path | None = None                                  # None = no logging
    clock: Callable[[], float] = field(default=time.perf_counter)


def _step(state: AgentState, name: str) -> list[str]:
    return [*state.get("path", []), name]


def _chunks(state: AgentState) -> list[RetrievedChunk]:
    return [RetrievedChunk(**c) for c in state.get("retrieved_chunks", [])]


def format_history(messages: list[AnyMessage], limit: int) -> str:
    """Trimming (SW8): the LLM sees only the last `limit` messages, shortened."""
    lines = []
    for m in messages[-limit:]:
        role = "Benutzer" if isinstance(m, HumanMessage) else "Assistent"
        lines.append(f"{role}: {str(m.content)[:600]}")
    return "\n".join(lines) or "(kein Verlauf)"


def make_nodes(deps: Dependencies) -> dict[str, Callable[[AgentState], dict]]:

    def normalize_query(state: AgentState) -> dict:
        raw = state["messages"][-1].content if state.get("messages") else ""
        query = normalize_text(str(raw), deps.max_query_chars)
        return {**PER_TURN_RESET, "turn_id": uuid.uuid4().hex[:12],
                "path": ["normalize_query"], "user_query": query, "standalone_query": query}

    def check_input_guardrails(state: AgentState) -> dict:
        result = check_input(state["user_query"])
        update = {"path": _step(state, "check_input_guardrails")}
        if result.blocked:
            update |= {"refusal_reason": result.reason, "guardrail_rule": result.rule_id}
        return update

    def classify_query(state: AgentState) -> dict:
        update: dict = {"path": _step(state, "classify_query")}
        history = format_history(state["messages"][:-1], deps.max_history_messages)
        try:
            c = deps.classify(history, state["user_query"])
        except Exception:  # noqa: BLE001 – fail closed (SW9)
            return update | {"refusal_reason": "technical_error"}
        update |= {"standalone_query": c.standalone_query.strip() or state["user_query"],
                   "category": c.category, "security_flag": c.security_flag,
                   "is_ambiguous": c.is_ambiguous,
                   "clarification_question": c.clarification_question}
        if c.security_flag != "none":
            update["refusal_reason"] = c.security_flag
        elif c.category == "out_of_scope":
            update["refusal_reason"] = "out_of_scope"
        return update

    def retrieve_documents(state: AgentState) -> dict:
        chunks = deps.retrieve(state["standalone_query"])
        return {"path": _step(state, "retrieve_documents"),
                "retrieved_chunks": [c.to_dict() for c in chunks]}

    def assess_evidence(state: AgentState) -> dict:
        update: dict = {"path": _step(state, "assess_evidence")}
        chunks = _chunks(state)
        dense = [c.dense_score for c in chunks if c.dense_score is not None]
        # Stage 1, deterministic: nothing found, or nothing similar enough.
        # (Pure BM25 mode has no dense scores -> stage 1 is skipped, not failed.)
        if not chunks or (dense and max(dense) < deps.min_dense_similarity):
            return update | {"evidence_status": "insufficient",
                             "missing_information": "Keine ausreichend ähnlichen Dokumente gefunden."}
        # Stage 2, LLM judgement: topic found – but is the answer there?
        try:
            a = deps.assess(state["standalone_query"], chunks)
        except Exception:  # noqa: BLE001 – fail closed
            return update | {"evidence_status": "insufficient",
                             "missing_information": "Evidenzprüfung technisch fehlgeschlagen."}
        known = {c.chunk_id for c in chunks}
        return update | {"evidence_status": a.status,
                         "supporting_chunk_ids": [i for i in a.supporting_chunk_ids if i in known],
                         "missing_information": a.missing_information}

    def generate_answer(state: AgentState) -> dict:
        chunks = _chunks(state)
        supporting = set(state.get("supporting_chunk_ids", []))
        context = [c for c in chunks if c.chunk_id in supporting] or chunks
        answer = llm_generate_answer(state["standalone_query"], context, deps.answer_llm)
        return {"path": _step(state, "generate_answer"), "answer": answer.text,
                "sources": answer.sources, "invalid_citations": answer.invalid_citations}

    def ask_clarification(state: AgentState) -> dict:
        question = state.get("clarification_question") or (
            "Können Sie Ihre Frage präzisieren? Welches Modell, welchen Bericht "
            "oder welche Kennzahl meinen Sie?")
        return {"path": _step(state, "ask_clarification"), "answer": question}

    def refuse_request(state: AgentState) -> dict:
        reason = state.get("refusal_reason") or "technical_error"
        return {"path": _step(state, "refuse_request"), "refusal_reason": reason,
                "answer": REFUSAL_TEXTS.get(reason, REFUSAL_TEXTS["technical_error"])}

    def escalate_to_expert(state: AgentState) -> dict:
        related = sorted({c.doc_id for c in _chunks(state)
                          if (c.dense_score or 0.0) >= deps.min_dense_similarity})
        missing = state.get("missing_information")
        text = "Dazu enthält die freigegebene Dokumentation keine verlässliche Antwort."
        if missing:
            text += f" {missing}"
        if related:
            text += (" Thematisch verwandt, aber ohne die gesuchte Angabe: "
                     + ", ".join(related) + ".")
        text += (f" Bitte wenden Sie sich an die {deps.escalation_contact}. "
                 "Ich habe die Frage als mögliche Dokumentationslücke vermerkt.")
        if deps.logs_dir:
            log_gap(deps.logs_dir, state.get("turn_id", ""), state["standalone_query"],
                    state.get("category"), missing, related)
        return {"path": _step(state, "escalate_to_expert"), "answer": text,
                "escalation_reason": missing or "insufficient_evidence"}

    def format_response(state: AgentState) -> dict:
        text, redacted = redact_output(state.get("answer") or "")
        if state.get("path", [])[-1:] == ["generate_answer"]:
            lines = []
            for s in state.get("sources", []):
                note = "" if s.get("status") in (None, "current") else f" – Status: {s['status']}"
                section = f" ({s['section']})" if s.get("section") else ""
                lines.append(f"- {s['doc_id']} {s['title']}{section}{note}")
            text += "\n\nQuellen:\n" + ("\n".join(lines) if lines else
                                        "- keine überprüfbare Quelle zitiert")
        if deps.logs_dir:
            log_turn(deps.logs_dir, {
                "turn_id": state.get("turn_id"), "path": state.get("path"),
                "category": state.get("category"), "security_flag": state.get("security_flag"),
                "guardrail_rule": state.get("guardrail_rule"),
                "refusal_reason": state.get("refusal_reason"),
                "evidence_status": state.get("evidence_status"),
                "retrieved": [(c["chunk_id"], c.get("dense_score"))
                              for c in state.get("retrieved_chunks", [])],
                "sources": [s["doc_id"] for s in state.get("sources", [])],
                "invalid_citations": state.get("invalid_citations", []),
                "redacted": redacted})
        return {"path": _step(state, "format_response"), "final_response": text,
                "messages": [AIMessage(content=text)]}

    return {f.__name__: f for f in [
        normalize_query, check_input_guardrails, classify_query, retrieve_documents,
        assess_evidence, generate_answer, ask_clarification, refuse_request,
        escalate_to_expert, format_response]}
