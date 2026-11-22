"""Retrieval-Experiment: Hit@k, MRR, Precision@k und Latenz.

Vergleicht Dense, BM25 und Hybrid (RRF) für beide Chunk-Grössen – gleiche Fragen,
gleiche Ground Truth, gleiches k. Folgefragen werden mit ihrer eigenständigen
Formulierung gesucht, damit nur die Suche gemessen wird.
Aufruf:  python scripts/evaluate_retrieval.py [--config small|large|all] [--mode dense|sparse|hybrid|all]
Ausgabe: data/evaluation/results_retrieval_<Zeitstempel>.csv
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.agent.runtime import make_retriever  # noqa: E402
from bi_agent.config import load_yaml_settings  # noqa: E402
from bi_agent.evaluation.metrics import hit_at_k, precision_at_k, reciprocal_rank  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", choices=["small", "large", "all"], default="all")
    parser.add_argument("--mode", choices=["dense", "sparse", "hybrid", "all"], default="all")
    args = parser.parse_args()

    ks = load_yaml_settings()["retrieval"]["eval_k"]
    depth = max(ks)
    questions = pd.read_csv(ROOT / "data" / "evaluation" / "eval_questions.csv", dtype=str).fillna("")
    questions = questions[questions["relevant_document_ids"] != ""]
    configs = ["small", "large"] if args.config == "all" else [args.config]
    modes = ["dense", "sparse", "hybrid"] if args.mode == "all" else [args.mode]

    rows = []
    for config in configs:
        for mode in modes:
            search = make_retriever(config=config, mode=mode, k=depth)
            search("Aufwärmen")  # first query loads the model; exclude from latency
            for _, q in questions.iterrows():
                query = q["standalone_question"] or q["question"]
                relevant = set(q["relevant_document_ids"].split(";"))
                t = time.perf_counter()
                hits = search(query)
                latency_ms = 1000 * (time.perf_counter() - t)
                ranked = [h.doc_id for h in hits]
                row = {"config": config, "mode": mode, "test_id": q["test_id"],
                       "category": q["category"], "split": q["split"],
                       "top_docs": ";".join(ranked), "latency_ms": round(latency_ms, 1),
                       "rr": reciprocal_rank(ranked, relevant, depth),
                       f"p@{depth}": precision_at_k(ranked, relevant, depth)}
                for k in ks:
                    row[f"hit@{k}"] = hit_at_k(ranked, relevant, k)
                rows.append(row)

    df = pd.DataFrame(rows)
    out = ROOT / "data" / "evaluation" / f"results_retrieval_{datetime.now():%Y%m%d_%H%M}.csv"
    df.to_csv(out, index=False)

    metric_cols = [f"hit@{k}" for k in ks] + ["rr", f"p@{depth}", "latency_ms"]
    summary = (df.groupby(["config", "mode"])[metric_cols].mean().round(3)
                 .rename(columns={"rr": "MRR", "latency_ms": "Ø ms"}))
    print(f"{df['test_id'].nunique()} Fragen pro Variante\n")
    print(summary.to_string())

    # Where do the methods disagree? Rank-1 hit per question and variant.
    pivot = df.pivot_table(index="test_id", columns=["config", "mode"], values="hit@1")
    differing = pivot[pivot.nunique(axis=1) > 1]
    print("\nFragen, bei denen sich Rang 1 je Variante unterscheidet (1 = richtig):")
    print(differing.astype(int).to_string() if len(differing) else "  keine")
    print(f"\nDetails: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
