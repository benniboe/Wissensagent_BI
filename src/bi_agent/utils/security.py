"""Mustererkennung für sensible Inhalte (Regex aus config/sensitive_patterns.yaml).

Genutzt vom Scanner (scripts/scan_sensitive.py) und von den Guardrails.
Grenze: Regex erkennt bekannte Formate, keine umschriebenen Secrets oder Namen
ohne Begriffsliste.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from bi_agent.config import PROJECT_ROOT

DEFAULT_PATTERN_FILE = PROJECT_ROOT / "config" / "sensitive_patterns.yaml"


@dataclass(frozen=True)
class Pattern:
    id: str
    category: str
    severity: str
    regex: re.Pattern[str]


@dataclass(frozen=True)
class Finding:
    pattern_id: str
    category: str
    severity: str
    start: int
    end: int
    masked_match: str


def mask(value: str, keep: int = 3) -> str:
    """Show only the first characters so reports do not re-leak secrets."""
    value = value.strip()
    if len(value) <= keep:
        return "*" * len(value)
    return value[:keep] + "*" * min(len(value) - keep, 12) + f" (len={len(value)})"


def _term_pattern(terms: list[str]) -> re.Pattern[str] | None:
    terms = [t.strip() for t in terms if t.strip() and not t.startswith("#")]
    if not terms:
        return None
    alternation = "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True))
    return re.compile(rf"(?i)(?<!\w)(?:{alternation})(?!\w)")


def load_patterns(path: Path | None = None, root: Path = PROJECT_ROOT) -> list[Pattern]:
    with (path or DEFAULT_PATTERN_FILE).open(encoding="utf-8") as fh:
        spec = yaml.safe_load(fh)
    patterns = [
        Pattern(p["id"], p["category"], p["severity"], re.compile(p["regex"]))
        for p in spec.get("patterns", [])
    ]
    for tl in spec.get("term_lists", []):
        term_file = root / tl["file"]
        if term_file.exists():
            compiled = _term_pattern(term_file.read_text(encoding="utf-8").splitlines())
            if compiled:
                patterns.append(Pattern(tl["id"], tl["category"], tl["severity"], compiled))
    return patterns


def scan_text(text: str, patterns: list[Pattern]) -> list[Finding]:
    findings: list[Finding] = []
    for p in patterns:
        for m in p.regex.finditer(text):
            findings.append(
                Finding(p.id, p.category, p.severity, m.start(), m.end(), mask(m.group(0)))
            )
    return sorted(findings, key=lambda f: (f.start, f.pattern_id))


def contains_blocking(text: str, patterns: list[Pattern]) -> bool:
    return any(f.severity == "block" for f in scan_text(text, patterns))
