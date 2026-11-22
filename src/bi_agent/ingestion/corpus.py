"""Lädt den Korpus: pro Datei ein SourceDocument mit Volltext und Strukturmarkern.

Die Marker sagen, wo eine Überschrift oder Seite beginnt. Das Chunking zerlegt
den Volltext und gibt jedem Chunk damit Abschnitt und Seite mit.
Metadaten stammen aus <korpus>/documents.yaml.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DISCLAIMER_PATTERN = re.compile(r"^>?\s*Synthetisches Beispieldokument.*$", re.M)
PDF_HEADING_PATTERN = re.compile(r"^\d+(\.\d+)*\.?\s+[A-ZÄÖÜ][^\n]{2,80}$")


@dataclass
class Marker:
    offset: int                # character position in SourceDocument.text
    heading: str | None = None
    page: int | None = None


@dataclass
class SourceDocument:
    text: str
    metadata: dict
    markers: list[Marker] = field(default_factory=list)

    def context_at(self, offset: int) -> tuple[str | None, int | None]:
        """Heading and page that apply at a given character position."""
        heading, page = None, None
        for m in self.markers:
            if m.offset > offset:
                break
            if m.heading is not None:
                heading = m.heading
            if m.page is not None:
                page = m.page
        return heading, page


class _Builder:
    """Collects text pieces and records markers at their offsets."""

    def __init__(self) -> None:
        self.parts: list[str] = []
        self.length = 0
        self.markers: list[Marker] = []

    def add(self, text: str, heading: str | None = None, page: int | None = None) -> None:
        text = text.strip()
        if not text:
            return
        if heading is not None or page is not None:
            self.markers.append(Marker(self.length, heading, page))
        self.parts.append(text)
        self.length += len(text) + 2  # +2 for the "\n\n" join

    def text(self) -> str:
        return "\n\n".join(self.parts)


def _strip_disclaimer(text: str) -> str:
    # The disclaimer is in metadata (synthetic: true); repeated in every
    # document it would only make all first chunks look alike.
    return DISCLAIMER_PATTERN.sub("", text)


def _load_markdown(path: Path) -> tuple[str, list[Marker]]:
    b = _Builder()
    block: list[str] = []
    for line in _strip_disclaimer(path.read_text(encoding="utf-8")).splitlines():
        if line.startswith("#"):
            b.add("\n".join(block))
            block = []
            b.add(line, heading=line.lstrip("#").strip())
        else:
            block.append(line)
    b.add("\n".join(block))
    return b.text(), b.markers


def _iter_docx_blocks(document):
    """Paragraphs and tables in document order (python-docx lists them separately)."""
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, document)
        elif child.tag.endswith("}tbl"):
            yield Table(child, document)


def _load_docx(path: Path) -> tuple[str, list[Marker]]:
    import docx
    from docx.table import Table

    b = _Builder()
    for block in _iter_docx_blocks(docx.Document(str(path))):
        if isinstance(block, Table):
            rows = [" | ".join(c.text.strip() for c in row.cells) for row in block.rows]
            b.add("\n".join(rows))
            continue
        text = _strip_disclaimer(block.text)
        style = (block.style.name or "") if block.style is not None else ""
        if style.startswith("Heading") or style == "Title":
            b.add(text, heading=text.strip())
        else:
            b.add(text)
    return b.text(), b.markers


def _load_pdf(path: Path) -> tuple[str, list[Marker]]:
    from pypdf import PdfReader

    b = _Builder()
    for page_no, page in enumerate(PdfReader(str(path)).pages, start=1):
        first_on_page = True
        for line in _strip_disclaimer(page.extract_text() or "").splitlines():
            heading = line.strip() if PDF_HEADING_PATTERN.match(line.strip()) else None
            b.add(line, heading=heading, page=page_no if first_on_page else None)
            if line.strip():
                first_on_page = False
    return b.text(), b.markers


LOADERS = {".md": _load_markdown, ".txt": _load_markdown, ".docx": _load_docx, ".pdf": _load_pdf}


def load_corpus(corpus_dir: Path) -> list[SourceDocument]:
    """Load every document listed in documents.yaml (unlisted files are ignored)."""
    spec = yaml.safe_load((corpus_dir / "documents.yaml").read_text(encoding="utf-8"))
    documents = []
    for meta in spec["documents"]:
        path = corpus_dir / meta["source_file"]
        text, markers = LOADERS[path.suffix.lower()](path)
        # Chroma accepts only str/int/float/bool metadata -> drop None values.
        clean_meta = {k: v for k, v in meta.items() if v is not None}
        documents.append(SourceDocument(text=text, metadata=clean_meta, markers=markers))
    return documents
