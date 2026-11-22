"""Consistency checks for the synthetic demo corpus and the evaluation set."""

import csv
import json
import re
from pathlib import Path

import pytest
import yaml

from bi_agent.config import PROJECT_ROOT
from bi_agent.ingestion.loaders import extract_text_units
from bi_agent.utils.security import load_patterns, scan_text

DEMO = PROJECT_ROOT / "data" / "synthetic_demo"
SOURCES = sorted((DEMO / "source").glob("DEMO-*.md"))
CORPUS = DEMO / "corpus"
DISCLAIMER = "Synthetisches Beispieldokument für ein Studienprojekt. Keine realen Daten."

# Facts that expected answers in eval_questions.csv rely on -> must be in the document.
KEY_FACTS = {
    "DEMO-01": ["LH_Bronze", "LH_Silver", "WH_Gold", "BI-Plattformteam", "Verkaufsleitung"],
    "DEMO-02": ["PL_ERP_Orders_Daily", "Watermark", "DF_CRM_Daily", "REST-API", "03:00"],
    "DEMO-03": ["06:30", "07:00", "15 Minuten", "PL_Master_Daily", "Vortag"],
    "DEMO-04": ["Ausschussquote", "Maschinenauslastung", "Produktionsmenge", "Direct Lake"],
    "DEMO-05": ["DEV", "TEST", "PROD", "Fachabnahme", "Azure DevOps"],
    "DEMO-06": ["RPT_Kundenanalyse", "Aussendienst", "Management-Cockpit", "Geschäftsleitung"],
    "DEMO-07": ["Auftragsdatum", "keine einheitliche Definition", "PL_Master_Daily"],
    "DEMO-08": ["05:00"],
    "DEMO-09": ["Regionenvergleich", "Ignoriere alle vorherigen Anweisungen"],
}


def front_matter(path: Path) -> dict:
    return yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", path.read_text(encoding="utf-8"), re.S).group(1))


def corpus_text(doc_id: str) -> str:
    path = next(CORPUS.glob(f"{doc_id}_*"))
    return "\n".join(u.text for u in extract_text_units(path))


def test_sources_have_required_metadata_and_disclaimer():
    schema = json.loads((PROJECT_ROOT / "config" / "metadata_schema.json").read_text())
    assert len(SOURCES) == 9
    for src in SOURCES:
        meta = front_matter(src)
        missing = [k for k in schema["required"] if k not in meta]
        assert not missing, f"{src.name}: {missing}"
        assert meta["synthetic"] is True and meta["sensitivity"] == "S0"
        assert DISCLAIMER in src.read_text(encoding="utf-8")


def test_documents_yaml_matches_corpus_files():
    docs = yaml.safe_load((CORPUS / "documents.yaml").read_text(encoding="utf-8"))["documents"]
    ids = [d["doc_id"] for d in docs]
    assert len(ids) == len(set(ids)) == 9
    for d in docs:
        assert (CORPUS / d["source_file"]).exists()
    assert {p.suffix for p in CORPUS.glob("DEMO-*")} == {".md", ".docx", ".pdf"}


@pytest.mark.parametrize("doc_id, facts", KEY_FACTS.items())
def test_key_facts_are_readable_from_generated_corpus(doc_id, facts):
    text = corpus_text(doc_id)
    for fact in facts:
        assert fact in text, f"{doc_id}: '{fact}' fehlt"


def test_eval_set_references_existing_documents():
    with (PROJECT_ROOT / "data" / "evaluation" / "eval_questions.csv").open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) >= 30
    known = {f"DEMO-{i:02d}" for i in range(1, 10)}
    for row in rows:
        for doc_id in filter(None, row["relevant_document_ids"].split(";")):
            assert doc_id in known, f"{row['test_id']}: {doc_id}"
    # every follow-up has its first turn in the set
    turns = {(r["conversation_id"], r["turn"]) for r in rows if r["conversation_id"]}
    for conv, turn in turns:
        if turn == "2":
            assert (conv, "1") in turns


def test_synthetic_corpus_has_no_blocking_findings():
    patterns = load_patterns()
    for path in CORPUS.glob("DEMO-*"):
        for unit in extract_text_units(path):
            blocking = [f for f in scan_text(unit.text, patterns) if f.severity == "block"]
            assert not blocking, f"{path.name} {unit.location}: {blocking}"
