"""Pydantic-Schemas für die strukturierte LLM-Ausgabe (Einordnung, Evidenz-Urteil).

Die Feldbeschreibungen sind Teil des Prompts.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["architecture", "data_sources", "kpi", "reports_models",
                   "operations", "responsibilities", "out_of_scope"]
SecurityFlag = Literal["none", "secret_request", "production_change",
                       "prompt_injection", "business_data_request"]


class QueryClassification(BaseModel):
    """Einordnung einer Benutzerfrage an den BI-Wissensassistenten."""

    standalone_query: str = Field(
        description="Frage, ohne Gesprächsverlauf verständlich formuliert")
    category: Category = Field(description="Themenbereich der Frage")
    is_ambiguous: bool = Field(
        description="true, wenn eine wesentliche Angabe fehlt und der Verlauf sie nicht klärt")
    clarification_question: str | None = Field(
        default=None, description="Gezielte Rückfrage, nur wenn is_ambiguous true ist")
    security_flag: SecurityFlag = Field(description="Sicherheitsrelevante Absicht der Frage")


class EvidenceAssessment(BaseModel):
    """Urteil, ob die Dokumentauszüge die Frage beantworten."""

    status: Literal["sufficient", "insufficient", "conflicting"] = Field(
        description="sufficient, insufficient oder conflicting")
    supporting_chunk_ids: list[str] = Field(
        default_factory=list, description="chunk-IDs der Auszüge, welche die Antwort tragen")
    missing_information: str | None = Field(
        default=None, description="Bei insufficient: was fehlt, ein kurzer Satz")
