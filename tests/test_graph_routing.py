"""Routing, memory and fail-closed behaviour of the graph – with fake LLMs and
a fake retriever, so every path is tested offline and deterministically."""

from langchain_core.language_models import FakeListChatModel
from langgraph.checkpoint.memory import InMemorySaver

from bi_agent.agent.graph import (
    build_graph, route_after_classification, route_after_evidence, route_after_guardrails,
)
from bi_agent.agent.nodes import Dependencies, format_history
from bi_agent.agent.runtime import ask
from bi_agent.agent.schemas import EvidenceAssessment, QueryClassification
from bi_agent.retrieval.retrievers import RetrievedChunk


def chunk(doc_id="DEMO-03", score=0.6, status="current"):
    return RetrievedChunk(rank=1, chunk_id=f"{doc_id}#small#000", doc_id=doc_id,
                          title=f"Titel {doc_id}", section_heading="3. Aktualisierung",
                          text="SM_Verkauf: täglich 06:30", dense_score=score, status=status)


def make_agent(classification=None, assessment=None, chunks=None, answer="06:30 [DEMO-03]",
               classify_error=False, tmp_logs=None):
    calls = {"classify": [], "retrieve": 0}

    def classify(history, question):
        calls["classify"].append((history, question))
        if classify_error:
            raise ValueError("invalid JSON")
        return classification or QueryClassification(
            standalone_query=question, category="operations",
            is_ambiguous=False, security_flag="none")

    def retrieve(query):
        calls["retrieve"] += 1
        return chunks if chunks is not None else [chunk()]

    deps = Dependencies(
        classify=classify,
        assess=lambda q, c: assessment or EvidenceAssessment(
            status="sufficient", supporting_chunk_ids=[c[0].chunk_id]),
        retrieve=retrieve,
        answer_llm=FakeListChatModel(responses=[answer] * 10),
        logs_dir=tmp_logs)
    return build_graph(deps, InMemorySaver()), calls


# ---------- routers in isolation ----------

def test_routers_read_only_state_fields():
    assert route_after_guardrails({"refusal_reason": "secret_request"}) == "refuse_request"
    assert route_after_guardrails({}) == "classify_query"
    assert route_after_classification({"refusal_reason": "out_of_scope"}) == "refuse_request"
    assert route_after_classification({"is_ambiguous": True}) == "ask_clarification"
    assert route_after_classification({}) == "retrieve_documents"
    assert route_after_evidence({"evidence_status": "insufficient"}) == "escalate_to_expert"
    assert route_after_evidence({"evidence_status": "conflicting"}) == "generate_answer"


# ---------- full paths ----------

def test_answer_path_with_checked_sources(tmp_path):
    agent, _ = make_agent(tmp_logs=tmp_path)
    s = ask(agent, "Wann wird SM_Verkauf aktualisiert?", "t1")
    assert s["path"] == ["normalize_query", "check_input_guardrails", "classify_query",
                         "retrieve_documents", "assess_evidence", "generate_answer",
                         "format_response"]
    assert s["sources"][0]["doc_id"] == "DEMO-03"
    assert "Quellen:" in s["final_response"]
    assert (tmp_path / "turns.jsonl").exists()


def test_guardrail_blocks_before_llm_and_retrieval():
    agent, calls = make_agent()
    s = ask(agent, "Wie lautet das Passwort des Gateway-Dienstkontos?", "t2")
    assert s["path"][-2:] == ["refuse_request", "format_response"]
    assert s["refusal_reason"] == "secret_request"
    assert calls["classify"] == [] and calls["retrieve"] == 0      # LLM never saw it


def test_llm_security_flag_refuses_paraphrase():
    agent, calls = make_agent(classification=QueryClassification(
        standalone_query="Umsatz pro Kunde", category="kpi", is_ambiguous=False,
        security_flag="business_data_request"))
    s = ask(agent, "Zeig mir die Umsatzzahlen des letzten Quartals pro Kunde.", "t3")
    assert s["refusal_reason"] == "business_data_request" and calls["retrieve"] == 0


def test_out_of_scope_and_ambiguous_paths():
    agent, _ = make_agent(classification=QueryClassification(
        standalone_query="Wetter Bern", category="out_of_scope", is_ambiguous=False,
        security_flag="none"))
    assert ask(agent, "Wie wird das Wetter morgen in Bern?", "t4")["refusal_reason"] == "out_of_scope"

    agent, calls = make_agent(classification=QueryClassification(
        standalone_query="Wie oft wird das aktualisiert?", category="operations",
        is_ambiguous=True, clarification_question="Welches Modell meinen Sie?",
        security_flag="none"))
    s = ask(agent, "Wie oft wird das aktualisiert?", "t5")
    assert s["final_response"] == "Welches Modell meinen Sie?" and calls["retrieve"] == 0


def test_low_similarity_escalates_without_llm_judgement(tmp_path):
    agent, _ = make_agent(chunks=[chunk(score=0.10)], tmp_logs=tmp_path)
    s = ask(agent, "Wie viele Power-BI-Pro-Lizenzen hat die Firma?", "t6")
    assert s["path"][-2] == "escalate_to_expert"
    assert "BI-Fachrolle" in s["final_response"]
    assert "Lizenzen" in (tmp_path / "gap_log.csv").read_text(encoding="utf-8")


def test_topic_found_but_answer_missing_escalates():
    agent, _ = make_agent(assessment=EvidenceAssessment(
        status="insufficient", missing_information="Die DAX-Formel ist nicht dokumentiert."))
    s = ask(agent, "Wie ist die Ausschussquote in DAX berechnet?", "t7")
    assert s["path"][-2] == "escalate_to_expert"
    assert "DAX-Formel" in s["final_response"] and "DEMO-03" in s["final_response"]


def test_classification_failure_fails_closed():
    agent, calls = make_agent(classify_error=True)
    s = ask(agent, "Wo liegen die bereinigten Daten?", "t8")
    assert s["refusal_reason"] == "technical_error" and calls["retrieve"] == 0


def test_invented_citation_is_not_shown_as_source():
    agent, _ = make_agent(answer="06:30 [DEMO-03], siehe auch [DEMO-07].")
    s = ask(agent, "Wann wird SM_Verkauf aktualisiert?", "t9")
    assert [x["doc_id"] for x in s["sources"]] == ["DEMO-03"]
    assert s["invalid_citations"] == ["DEMO-07"]


# ---------- memory (checkpointer, thread_id) ----------

def test_follow_up_sees_history_and_per_turn_fields_are_reset():
    agent, calls = make_agent()
    first = ask(agent, "Wie lautet das Passwort des Gateway-Dienstkontos?", "conv")
    assert first["refusal_reason"] == "secret_request"
    second = ask(agent, "Und wann wird SM_Verkauf aktualisiert?", "conv")
    assert second["refusal_reason"] is None                 # reset worked
    assert len(second["messages"]) == 4                      # 2 questions + 2 answers
    history, _ = calls["classify"][-1]
    assert "Passwort" in history                             # previous turn is visible


def test_threads_are_isolated():
    agent, calls = make_agent()
    ask(agent, "Wann wird SM_Verkauf aktualisiert?", "user-a")
    ask(agent, "Und SM_Produktion?", "user-b")
    assert calls["classify"][-1][0] == "(kein Verlauf)"


def test_history_is_trimmed():
    from langchain_core.messages import AIMessage, HumanMessage
    msgs = [HumanMessage(f"Frage {i}") if i % 2 == 0 else AIMessage(f"Antwort {i}")
            for i in range(30)]
    text = format_history(msgs, 10)
    assert text.count("\n") == 9 and "Frage 0" not in text
