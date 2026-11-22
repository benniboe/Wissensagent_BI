"""Textextraktion aus PDF, DOCX, Markdown und TXT.

Liefert Texteinheiten mit Fundstelle (Seite oder Absatz), damit der Scanner
für sensible Inhalte die genaue Stelle angeben kann.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".md", ".txt"}


@dataclass(frozen=True)
class TextUnit:
    location: str  # e.g. "page 3", "paragraph 12", "line 40"
    text: str


def _pdf_units(path: Path) -> list[TextUnit]:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [
        TextUnit(f"page {i}", page.extract_text() or "")
        for i, page in enumerate(reader.pages, start=1)
    ]


def _docx_units(path: Path) -> list[TextUnit]:
    import docx

    document = docx.Document(str(path))
    units = [
        TextUnit(f"paragraph {i}", p.text)
        for i, p in enumerate(document.paragraphs, start=1)
        if p.text.strip()
    ]
    # Tables often hold server names, owners and schedules – scan them too.
    for t_idx, table in enumerate(document.tables, start=1):
        for r_idx, row in enumerate(table.rows, start=1):
            cells = " | ".join(c.text for c in row.cells)
            if cells.strip(" |"):
                units.append(TextUnit(f"table {t_idx} row {r_idx}", cells))
    # Headers/footers frequently contain names and classification marks.
    for s_idx, section in enumerate(document.sections, start=1):
        for kind, part in (("header", section.header), ("footer", section.footer)):
            text = "\n".join(p.text for p in part.paragraphs if p.text.strip())
            if text:
                units.append(TextUnit(f"section {s_idx} {kind}", text))
    return units


def _text_units(path: Path) -> list[TextUnit]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return [TextUnit(f"line {i}", line) for i, line in enumerate(lines, start=1) if line.strip()]


def extract_text_units(path: Path) -> list[TextUnit]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _pdf_units(path)
    if suffix == ".docx":
        return _docx_units(path)
    if suffix in {".md", ".txt"}:
        return _text_units(path)
    raise ValueError(f"Nicht unterstütztes Format: {path.suffix}")


def docx_core_properties(path: Path) -> dict[str, str]:
    """Author/last_modified_by are personal data hidden in file metadata."""
    import docx

    props = docx.Document(str(path)).core_properties
    return {
        "author": props.author or "",
        "last_modified_by": props.last_modified_by or "",
        "title": props.title or "",
        "comments": props.comments or "",
    }
