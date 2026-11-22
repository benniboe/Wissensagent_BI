"""Deterministische Guardrails: Regeln im Code statt Urteil des LLM.

Eingabe: Regex-Regeln aus config/guardrails.yaml (Secrets, Änderungen, Injection)
         plus Secret-Formate aus config/sensitive_patterns.yaml -> fester Ablehnungstext.
Ausgabe: Secret-Formate in der Antwort werden geschwärzt.
Grenze:  Umschreibungen und andere Sprachen gehen durch; zweite Schicht ist das
         Sicherheits-Flag der LLM-Einordnung.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache

import yaml

from bi_agent.config import PROJECT_ROOT
from bi_agent.utils.security import Pattern, load_patterns, scan_text

# Fixed refusal texts – written by us, not by the LLM, so they cannot be manipulated.
REFUSAL_TEXTS = {
    "secret_request": (
        "Passwörter, Schlüssel und andere Zugangsdaten gebe ich nicht aus. "
        "Zugangsdaten werden in den Verbindungseinstellungen von Fabric verwaltet; "
        "zuständig ist das BI-Plattformteam."),
    "secret_in_input": (
        "Ihre Nachricht scheint Zugangsdaten oder einen Schlüssel zu enthalten. "
        "Ich verarbeite sie deshalb nicht. Bitte entfernen Sie den Wert und fragen Sie erneut."),
    "production_change": (
        "Ich bin ein reiner Auskunfts-Prototyp und führe keine Änderungen an Workspaces, "
        "Pipelines, Modellen oder Berichten aus. Änderungen nimmt das BI-Plattformteam vor."),
    "prompt_injection": (
        "Diese Anfrage versucht, meine Regeln zu ändern. Das führe ich nicht aus. "
        "Gern beantworte ich Fragen zur BI-Plattform."),
    "business_data_request": (
        "Konkrete Geschäftszahlen gebe ich nicht aus – ich habe keinen Zugriff auf "
        "produktive Daten. Die Werte finden Sie im zuständigen Power-BI-Bericht."),
    "out_of_scope": (
        "Dazu kann ich nichts sagen. Ich beantworte nur Fragen zur BI-Plattform "
        "der Beispiel AG (Architektur, Datenflüsse, Modelle, Berichte, Betrieb)."),
    "technical_error": (
        "Ich konnte Ihre Frage gerade nicht sicher verarbeiten. Bitte versuchen Sie es "
        "erneut oder wenden Sie sich an die BI-Fachrolle."),
}


@dataclass(frozen=True)
class GuardrailResult:
    blocked: bool
    reason: str | None = None
    rule_id: str | None = None


@lru_cache(maxsize=1)
def _input_rules() -> tuple[list[tuple[str, str, re.Pattern[str]]], set[str]]:
    with (PROJECT_ROOT / "config" / "guardrails.yaml").open(encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    rules = [(r["id"], r["reason"], re.compile(r["regex"])) for r in spec["input_rules"]]
    return rules, set(spec.get("block_secret_categories_in_input", []))


@lru_cache(maxsize=1)
def _sensitive_patterns() -> list[Pattern]:
    return load_patterns()


def normalize_text(text: str, max_chars: int) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def check_input(text: str) -> GuardrailResult:
    rules, secret_categories = _input_rules()
    for rule_id, reason, pattern in rules:
        if pattern.search(text):
            return GuardrailResult(True, reason, rule_id)
    for finding in scan_text(text, _sensitive_patterns()):
        if finding.category in secret_categories and finding.severity == "block":
            return GuardrailResult(True, "secret_in_input", finding.pattern_id)
    return GuardrailResult(False)


def redact_output(text: str) -> tuple[str, list[str]]:
    """Replace secret formats in an answer (should never happen with a clean corpus)."""
    findings = [f for f in scan_text(text, _sensitive_patterns())
                if f.category == "secret" and f.severity == "block"]
    for f in sorted(findings, key=lambda f: f.start, reverse=True):
        text = text[:f.start] + "[entfernt]" + text[f.end:]
    return text, [f.pattern_id for f in findings]
