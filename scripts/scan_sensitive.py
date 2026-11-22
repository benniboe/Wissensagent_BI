"""Sucht in Dokumenten nach sensiblen Inhalten (Secrets, Personendaten, ...).

Aufruf: python scripts/scan_sensitive.py <ordner> [--out data/review/scan_report.csv]
Der Bericht enthält nur maskierte Treffer; 'block'-Treffer müssen vor einer
Freigabe 0 sein. Der Ausgabeordner data/review/ ist von Git ausgeschlossen.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.ingestion.loaders import (  # noqa: E402
    SUPPORTED_SUFFIXES,
    docx_core_properties,
    extract_text_units,
)
from bi_agent.utils.security import load_patterns, mask, scan_text  # noqa: E402

FIELDS = ["file", "location", "pattern_id", "category", "severity", "masked_match", "decision"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "data" / "review" / "scan_report.csv")
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(f"Ordner nicht gefunden: {args.input_dir}")
        return 2

    patterns = load_patterns()
    files = sorted(p for p in args.input_dir.rglob("*") if p.suffix.lower() in SUPPORTED_SUFFIXES)
    rows: list[dict[str, str]] = []
    unreadable: list[str] = []

    for path in files:
        rel = str(path.relative_to(args.input_dir))
        try:
            units = extract_text_units(path)
        except Exception as exc:  # noqa: BLE001
            unreadable.append(f"{rel} ({type(exc).__name__})")
            continue
        if path.suffix.lower() == ".pdf" and not any(u.text.strip() for u in units):
            unreadable.append(f"{rel} (kein Textlayer – evtl. gescannt, manuell prüfen)")
        if path.suffix.lower() == ".docx":
            for key, value in docx_core_properties(path).items():
                if value.strip():
                    rows.append(dict(file=rel, location=f"file property {key}",
                                     pattern_id="META_DOCX_PROPERTY", category="personal_data",
                                     severity="review", masked_match=mask(value), decision=""))
        for unit in units:
            for f in scan_text(unit.text, patterns):
                rows.append(dict(file=rel, location=unit.location, pattern_id=f.pattern_id,
                                 category=f.category, severity=f.severity,
                                 masked_match=f.masked_match, decision=""))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    by_sev = Counter(r["severity"] for r in rows)
    print(f"{len(files)} Dateien gescannt, {len(rows)} Fundstellen "
          f"(block: {by_sev.get('block', 0)}, review: {by_sev.get('review', 0)})")
    for (file, sev), n in sorted(Counter((r['file'], r['severity']) for r in rows).items()):
        print(f"  {file}: {n} x {sev}")
    for u in unreadable:
        print(f"  NICHT GELESEN: {u}")
    print(f"Report: {args.out}")
    print("Hinweis: 0 Fundstellen heisst NICHT 'sauber' – manuelle Endkontrolle bleibt Pflicht.")
    return 1 if by_sev.get("block", 0) else 0


if __name__ == "__main__":
    raise SystemExit(main())
