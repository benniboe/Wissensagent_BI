"""Streamlit-Oberfläche des Agenten.

Start: streamlit run app.py
Eine Browser-Sitzung = eine thread_id, damit Folgefragen den Verlauf kennen.
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from bi_agent.agent.runtime import ask, build_agent, build_dependencies, make_retriever  # noqa: E402
from bi_agent.config import load_yaml_settings  # noqa: E402

NODE_LABELS = {
    "normalize_query": "Eingabe", "check_input_guardrails": "Sicherheitsprüfung",
    "classify_query": "Einordnung", "retrieve_documents": "Suche",
    "assess_evidence": "Evidenzprüfung", "generate_answer": "Antwort",
    "ask_clarification": "Rückfrage", "refuse_request": "Ablehnung",
    "escalate_to_expert": "Eskalation", "format_response": "Ausgabe",
}
EXAMPLES = [
    "Wo liegen die bereinigten, aber noch nicht aggregierten Daten?",
    "Welche Reports basieren auf dem semantischen Modell Verkauf?",
    "Und wie oft wird dieses Modell aktualisiert?",
    "Wie ist die Ausschussquote im Modell SM_Produktion in DAX berechnet?",
    "Wie lautet das Passwort des Gateway-Dienstkontos?",
]

st.set_page_config(page_title="BI-Wissensagent", page_icon="📊", layout="wide")


@st.cache_resource(show_spinner="Lade Agent (Embedding-Modell und Index) …")
def get_agent(mode: str):
    return build_agent(build_dependencies(retrieve=make_retriever(mode=mode)))


def new_session() -> None:
    st.session_state.thread_id = uuid.uuid4().hex[:8]
    st.session_state.turns = []


if "thread_id" not in st.session_state:
    new_session()

settings = load_yaml_settings()
default_mode = settings["retrieval"]["default_mode"]

# ---------------------------------------------------------------- Seitenleiste
with st.sidebar:
    st.header("Einstellungen")
    modes = ["hybrid", "dense", "sparse"]
    mode = st.radio("Suchverfahren", modes, index=modes.index(default_mode),
                    format_func={"hybrid": "Hybrid (Dense + BM25, RRF)", "dense": "Dense (Embeddings)",
                                 "sparse": "BM25 (Stichworte)"}.get,
                    help="Ein Wechsel startet eine neue Sitzung.")
    if st.session_state.get("mode") not in (None, mode):
        new_session()
    st.session_state.mode = mode
    show_details = st.toggle("Details anzeigen (Pfad, Scores)", value=True)
    if st.button("Neue Sitzung", use_container_width=True):
        new_session()
        st.rerun()
    st.caption(f"Sitzung `{st.session_state.thread_id}` · Chunking "
               f"`{settings['chunking']['default']}` · Schwelle "
               f"`{settings['retrieval']['min_dense_similarity']}`")

    st.divider()
    st.subheader("Beispielfragen")
    for i, example in enumerate(EXAMPLES):
        if st.button(example, key=f"ex{i}", use_container_width=True):
            st.session_state.pending = example
            st.rerun()

    gap_log = ROOT / settings["agent"].get("logs_dir", "logs") / "gap_log.csv"
    if gap_log.exists():
        st.divider()
        st.subheader("Lückenprotokoll")
        lines = gap_log.read_text(encoding="utf-8").strip().splitlines()[1:]
        st.caption(f"{len(lines)} Fragen ohne verlässliche Antwort erfasst")

# ---------------------------------------------------------------- Hauptbereich
st.title("BI-Wissensagent")
st.caption("FHNW-Prototyp · Antworten nur aus freigegebener Dokumentation · "
           "**synthetische Daten der fiktiven Beispiel AG** · nur lesend")


def render_details(turn: dict) -> None:
    path = " → ".join(NODE_LABELS.get(n, n) for n in turn["path"] if n not in
                      ("normalize_query", "format_response"))
    st.caption(f"Weg: {path} · {turn['seconds']:.1f} s")
    if turn["chunks"]:
        with st.expander(f"Gefundene Abschnitte ({len(turn['chunks'])}) · Evidenz: "
                         f"{turn['evidence'] or '–'}"):
            rows = [{"Rang": c["rank"], "Abschnitt": c["chunk_id"],
                     "Kapitel": c.get("section_heading") or "",
                     "Dense": c.get("dense_score"), "BM25": c.get("bm25_score"),
                     "RRF": c.get("rrf_score"), "Status": c.get("status")}
                    for c in turn["chunks"]]
            st.dataframe(rows, hide_index=True, use_container_width=True)
    if turn.get("invalid"):
        st.warning(f"Zitiert, aber nicht gefunden (nicht als Quelle gezählt): {turn['invalid']}")


for turn in st.session_state.turns:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    with st.chat_message("assistant"):
        st.markdown(turn["answer"])
        if show_details:
            render_details(turn)

question = st.chat_input("Frage zur BI-Plattform …") or st.session_state.pop("pending", None)
if question:
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Suche und prüfe Evidenz …"):
            t = time.perf_counter()
            try:
                state = ask(get_agent(mode), question, st.session_state.thread_id)
                turn = {"question": question, "answer": state["final_response"],
                        "path": state["path"], "chunks": state.get("retrieved_chunks", []),
                        "evidence": state.get("evidence_status"),
                        "invalid": state.get("invalid_citations", []),
                        "seconds": time.perf_counter() - t}
            except Exception as exc:  # noqa: BLE001
                turn = {"question": question, "path": [], "chunks": [], "evidence": None,
                        "seconds": time.perf_counter() - t,
                        "answer": f"Technischer Fehler: {type(exc).__name__}. "
                                  "Bitte LiteLLM-Verbindung prüfen (scripts/check_llm.py)."}
        st.markdown(turn["answer"])
        if show_details:
            render_details(turn)
    st.session_state.turns.append(turn)
