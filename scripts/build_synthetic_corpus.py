"""Erzeugt den synthetischen Demo-Korpus (fiktive «Beispiel AG»).

Quelle:  data/synthetic_demo/source/DEMO-xx_*.md
Ausgabe: data/synthetic_demo/corpus/ – Markdown, einzelne Dokumente als DOCX/PDF
         (damit alle Loader getestet werden) und documents.yaml (Metadaten).
Aufruf:  python scripts/build_synthetic_corpus.py
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "synthetic_demo" / "source"
CORPUS_DIR = ROOT / "data" / "synthetic_demo" / "corpus"

# Which documents are rendered in which format (all others stay Markdown).
OUTPUT_FORMAT = {"DEMO-02": "docx", "DEMO-03": "docx", "DEMO-04": "pdf"}
FIXED_DATE = dt.datetime(2026, 11, 18, 12, 0, tzinfo=dt.timezone.utc)  # reproducible files


def split_front_matter(text: str) -> tuple[dict, str]:
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError("Front matter fehlt")
    return yaml.safe_load(match.group(1)), match.group(2).lstrip()


def strip_inline(text: str) -> str:
    """Remove Markdown emphasis and code marks for DOCX/PDF output."""
    return text.replace("**", "").replace("`", "")


def parse_blocks(body: str) -> list[tuple[str, object]]:
    """Tiny Markdown parser: heading, paragraph, bullet, numbered, quote, table."""
    blocks: list[tuple[str, object]] = []
    lines = body.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append((f"h{level}", strip_inline(line.lstrip("#").strip())))
        elif line.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [strip_inline(c.strip()) for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r":?-{3,}:?", c) for c in cells):
                    rows.append(cells)
                i += 1
            blocks.append(("table", rows))
            continue
        elif line.startswith("> "):
            blocks.append(("quote", strip_inline(line[2:])))
        elif line.startswith("- "):
            blocks.append(("bullet", strip_inline(line[2:])))
        elif re.match(r"^\d+\. ", line):
            blocks.append(("number", strip_inline(line)))
        else:
            blocks.append(("para", strip_inline(line)))
        i += 1
    return blocks


def write_docx(blocks, path: Path, title: str) -> None:
    import docx

    document = docx.Document()
    props = document.core_properties
    props.author = "Beispiel AG (synthetisch)"
    props.last_modified_by = ""
    props.comments = ""
    props.title = title
    props.created = props.modified = FIXED_DATE.replace(tzinfo=None)
    for kind, value in blocks:
        if kind.startswith("h"):
            document.add_heading(value, level=min(int(kind[1:]), 3))
        elif kind == "table":
            table = document.add_table(rows=len(value), cols=len(value[0]))
            table.style = "Table Grid"
            for r, row in enumerate(value):
                for c, cell in enumerate(row):
                    table.cell(r, c).text = cell
        elif kind == "bullet":
            document.add_paragraph(value, style="List Bullet")
        elif kind == "quote":
            document.add_paragraph(value, style="Intense Quote")
        else:  # para, number (keeps its "1." prefix)
            document.add_paragraph(value)
    document.save(str(path))


PDF_REPLACEMENTS = {"–": "-", "—": "-", "→": "->", "’": "'", "„": '"', "“": '"', "”": '"'}


def latin1(text: str) -> str:
    for src, dst in PDF_REPLACEMENTS.items():
        text = text.replace(src, dst)
    return text.encode("latin-1", errors="replace").decode("latin-1")


def write_pdf(blocks, path: Path, title: str) -> None:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_creation_date(FIXED_DATE)
    pdf.set_title(latin1(title))
    pdf.set_author("Beispiel AG (synthetisch)")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    sizes = {"h1": 16, "h2": 13, "h3": 11}
    for kind, value in blocks:
        if kind in sizes:
            pdf.ln(3)
            pdf.set_font("Helvetica", "B", sizes[kind])
            pdf.multi_cell(0, 7, latin1(value), new_x="LMARGIN", new_y="NEXT")
        elif kind == "table":
            pdf.set_font("Helvetica", size=9)
            with pdf.table(first_row_as_headings=True, line_height=5) as table:
                for row in value:
                    tr = table.row()
                    for cell in row:
                        tr.cell(latin1(cell))
            pdf.ln(2)
        else:
            pdf.set_font("Helvetica", "I" if kind == "quote" else "", 10)
            prefix = "- " if kind == "bullet" else ""
            pdf.multi_cell(0, 5, latin1(prefix + value), new_x="LMARGIN", new_y="NEXT")
            pdf.ln(1)
    pdf.output(str(path))


def main() -> int:
    sources = sorted(SOURCE_DIR.glob("DEMO-*.md"))
    if not sources:
        print(f"Keine Quellen in {SOURCE_DIR}")
        return 1
    if CORPUS_DIR.exists():
        shutil.rmtree(CORPUS_DIR)
    CORPUS_DIR.mkdir(parents=True)

    metadata: list[dict] = []
    for src in sources:
        meta, body = split_front_matter(src.read_text(encoding="utf-8"))
        fmt = OUTPUT_FORMAT.get(meta["doc_id"], "md")
        out = CORPUS_DIR / f"{src.stem}.{fmt}"
        if fmt == "md":
            out.write_text(body, encoding="utf-8")
        elif fmt == "docx":
            write_docx(parse_blocks(body), out, meta["title"])
        else:
            write_pdf(parse_blocks(body), out, meta["title"])
        meta["source_file"] = out.name
        metadata.append({k: (str(v) if isinstance(v, dt.date) else v) for k, v in meta.items()})
        print(f"  {meta['doc_id']}  {fmt:4}  {out.name}")

    with (CORPUS_DIR / "documents.yaml").open("w", encoding="utf-8") as fh:
        yaml.safe_dump({"documents": metadata}, fh, allow_unicode=True, sort_keys=False)
    print(f"{len(metadata)} Dokumente nach {CORPUS_DIR.relative_to(ROOT)} geschrieben.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
