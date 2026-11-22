"""Verdrahtung des Graphen: Nodes, Kanten und drei bedingte Kanten (Router).

Router lesen nur Zustandsfelder (kein LLM-Aufruf) und sind einzeln getestet.
Die vier geforderten Entscheidungen:
  sicher / sicherheitskritisch -> route_after_guardrails, route_after_classification
  im Scope / ausserhalb        -> route_after_classification
  klar / mehrdeutig            -> route_after_classification
  genug / zu wenig Evidenz     -> route_after_evidence
"""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from bi_agent.agent.nodes import Dependencies, make_nodes
from bi_agent.agent.state import AgentState


def route_after_guardrails(state: AgentState) -> str:
    return "refuse_request" if state.get("refusal_reason") else "classify_query"


def route_after_classification(state: AgentState) -> str:
    if state.get("refusal_reason"):        # security flag, out of scope or error
        return "refuse_request"
    if state.get("is_ambiguous"):
        return "ask_clarification"
    return "retrieve_documents"


def route_after_evidence(state: AgentState) -> str:
    return "escalate_to_expert" if state.get("evidence_status") == "insufficient" else "generate_answer"


def build_graph(deps: Dependencies, checkpointer=None):
    nodes = make_nodes(deps)
    builder = StateGraph(AgentState)
    for name, fn in nodes.items():
        builder.add_node(name, fn)

    builder.add_edge(START, "normalize_query")
    builder.add_edge("normalize_query", "check_input_guardrails")
    builder.add_conditional_edges("check_input_guardrails", route_after_guardrails,
                                  ["refuse_request", "classify_query"])
    builder.add_conditional_edges("classify_query", route_after_classification,
                                  ["refuse_request", "ask_clarification", "retrieve_documents"])
    builder.add_edge("retrieve_documents", "assess_evidence")
    builder.add_conditional_edges("assess_evidence", route_after_evidence,
                                  ["escalate_to_expert", "generate_answer"])
    for end_node in ["generate_answer", "ask_clarification", "refuse_request", "escalate_to_expert"]:
        builder.add_edge(end_node, "format_response")
    builder.add_edge("format_response", END)
    return builder.compile(checkpointer=checkpointer)
