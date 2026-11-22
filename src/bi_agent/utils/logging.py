"""Lokales Logging.

- logs/turns.jsonl  eine Zeile pro Frage: Route, Pfad, Zeit, Quellen
- logs/gap_log.csv  Fragen, die der Agent nicht beantworten konnte = Dokumentationslücken
Logs sind von Git ausgeschlossen und enthalten keine API-Schlüssel.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

GAP_FIELDS = ["timestamp", "turn_id", "question", "category", "reason", "related_docs"]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log_turn(logs_dir: Path, record: dict) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    with (logs_dir / "turns.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"timestamp": _now(), **record}, ensure_ascii=False) + "\n")


def log_gap(logs_dir: Path, turn_id: str, question: str, category: str | None,
            reason: str | None, related_docs: list[str]) -> None:
    logs_dir.mkdir(parents=True, exist_ok=True)
    path = logs_dir / "gap_log.csv"
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=GAP_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({"timestamp": _now(), "turn_id": turn_id, "question": question,
                         "category": category or "", "reason": reason or "",
                         "related_docs": ";".join(related_docs)})
