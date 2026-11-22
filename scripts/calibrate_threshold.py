"""Hilft, die Schwelle für Stufe 1 des Evidenz-Checks zu wählen.

Zeigt die beste Dense-Ähnlichkeit pro Testfrage, getrennt nach «soll antworten»
und «soll eskalieren». Gewählt wird nur anhand der Dev-Fragen; Test-Fragen
werden nur zur Information gezeigt (kein Tuning auf dem Testset).
Aufruf: python scripts/calibrate_threshold.py [--config small]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.agent.runtime import default_chunking_config  # noqa: E402
from bi_agent.config import load_yaml_settings  # noqa: E402
from bi_agent.retrieval.index import collection_name, get_embeddings, load_dense_index  # noqa: E402
from bi_agent.retrieval.retrievers import dense_search  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    args = parser.parse_args()
    config = args.config or default_chunking_config()
    current = load_yaml_settings()["retrieval"]["min_dense_similarity"]

    df = pd.read_csv(ROOT / "data" / "evaluation" / "eval_questions.csv", dtype=str).fillna("")
    # Questions stopped by the guardrail or the classifier never reach the evidence check.
    df = df[~df["expected_behavior"].isin(["refuse_security", "refuse_out_of_scope",
                                           "ask_clarification"])]
    store = load_dense_index(collection_name("synthetic_demo", config), get_embeddings())

    rows = []
    for _, q in df.iterrows():
        query = q["standalone_question"] or q["question"]
        top = dense_search(store, query, 1)[0]
        group = "soll eskalieren" if q["expected_behavior"] == "escalate" else "soll antworten"
        rows.append({"test_id": q["test_id"], "split": q["split"], "group": group,
                     "best_score": top.dense_score, "best_doc": top.doc_id,
                     "expected": q["expected_behavior"]})
    res = pd.DataFrame(rows).sort_values("best_score")
    print(f"Konfiguration {config}, aktuelle Schwelle {current}\n")
    print(res.to_string(index=False))
    print("\nZusammenfassung (min / max je Gruppe):")
    print(res.groupby(["group", "split"])["best_score"].agg(["min", "max", "count"]).round(3))
    print("\nHinweis: Stufe 1 soll nur offensichtlich Unpassendes aussortieren. Fragen, deren "
          "Thema im Korpus vorkommt, deren Antwort aber fehlt (z. B. T08), muss Stufe 2 "
          "(LLM-Urteil) erkennen – sie liegen oft über jeder sinnvollen Schwelle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
