"""Chat mit dem Agenten im Terminal (eine Sitzung = eine thread_id).

Aufruf: python scripts/chat.py [--debug]     Befehle: /neu = neue Sitzung, /ende = beenden
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.agent.runtime import ask, build_agent  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--debug", action="store_true", help="Pfad, Scores und Status anzeigen")
    args = parser.parse_args()

    print("Lade Agent (Embedding-Modell, Index) …")
    agent = build_agent()
    thread_id = uuid.uuid4().hex[:8]
    print(f"Bereit. Sitzung {thread_id}. Befehle: /neu, /ende\n")

    while True:
        try:
            question = input("Sie: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not question:
            continue
        if question == "/ende":
            break
        if question == "/neu":
            thread_id = uuid.uuid4().hex[:8]
            print(f"Neue Sitzung {thread_id}.\n")
            continue
        t = time.perf_counter()
        state = ask(agent, question, thread_id)
        print(f"\nAgent: {state['final_response']}\n")
        if args.debug:
            print(f"  Pfad:      {' > '.join(state['path'])}")
            print(f"  Frage:     {state.get('standalone_query')}")
            print(f"  Kategorie: {state.get('category')} | Sicherheit: {state.get('security_flag')} "
                  f"| Regel: {state.get('guardrail_rule')}")
            print(f"  Evidenz:   {state.get('evidence_status')} | "
                  + ", ".join(f"{c['chunk_id']} ({c['dense_score']:.2f})"
                              for c in state.get("retrieved_chunks", [])))
            if state.get("invalid_citations"):
                print(f"  WARNUNG erfundene Zitate: {state['invalid_citations']}")
            print(f"  Zeit:      {time.perf_counter() - t:.1f} s\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
