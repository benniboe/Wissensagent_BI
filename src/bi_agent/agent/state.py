"""Zustand des Agenten (AgentState).

Nur `messages` bleibt über mehrere Fragen erhalten. Alle anderen Felder gehören
zu EINER Frage und werden in normalize_query zurückgesetzt – sonst würde der
Checkpointer z. B. einen alten Ablehnungsgrund in die nächste Frage tragen.
"""

from __future__ import annotations

from typing import Annotated, Literal, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

EvidenceStatus = Literal["sufficient", "insufficient", "conflicting"]


class AgentState(TypedDict, total=False):
    # kept across turns (checkpointer, thread_id)
    messages: Annotated[list[AnyMessage], add_messages]

    # per turn – reset in normalize_query
    turn_id: str
    path: list[str]                     # visited nodes, for trajectory evaluation
    user_query: str
    standalone_query: str
    category: str | None
    security_flag: str | None
    is_ambiguous: bool
    clarification_question: str | None
    retrieved_chunks: list[dict]        # RetrievedChunk.to_dict()
    evidence_status: EvidenceStatus | None
    supporting_chunk_ids: list[str]
    missing_information: str | None
    answer: str | None                  # raw answer text (before formatting)
    sources: list[dict]
    invalid_citations: list[str]
    refusal_reason: str | None
    escalation_reason: str | None
    guardrail_rule: str | None
    final_response: str | None


PER_TURN_RESET: dict = {
    "category": None, "security_flag": None, "is_ambiguous": False,
    "clarification_question": None, "retrieved_chunks": [], "evidence_status": None,
    "supporting_chunk_ids": [], "missing_information": None, "answer": None,
    "sources": [], "invalid_citations": [], "refusal_reason": None,
    "escalation_reason": None, "guardrail_rule": None, "final_response": None,
}
