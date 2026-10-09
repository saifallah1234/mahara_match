from __future__ import annotations

from collections.abc import Callable
from time import monotonic
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class JobMatchingState(TypedDict, total=False):
    actor: Any
    prompt: str
    supported: bool
    evidence: dict[str, Any]
    reply: str
    error_code: str
    tool_call: dict[str, Any]


MatchTool = Callable[[Any], dict[str, Any]]
Explainer = Callable[[str, dict[str, Any]], str]


def build_job_matching_graph(match_tool: MatchTool, explain: Explainer) -> Any:
    def route(state: JobMatchingState) -> str:
        return "retrieve_matches" if state["supported"] else "explain_matches"

    def retrieve(state: JobMatchingState) -> dict[str, Any]:
        started = monotonic()
        try:
            evidence = match_tool(state["actor"])
            tool_call = {
                "tool_name": "get_candidate_job_matches",
                "input": {},
                "output": evidence,
                "status": "SUCCEEDED",
                "latency_ms": int((monotonic() - started) * 1000),
                "error_code": "",
            }
            return {"evidence": evidence, "tool_call": tool_call}
        except Exception:
            return {
                "error_code": "matching_failed",
                "tool_call": {
                    "tool_name": "get_candidate_job_matches",
                    "input": {},
                    "output": {},
                    "status": "FAILED",
                    "latency_ms": int((monotonic() - started) * 1000),
                    "error_code": "matching_failed",
                },
            }

    def explain_matches(state: JobMatchingState) -> dict[str, str]:
        if not state["supported"]:
            return {
                "reply": "I can help find jobs that match your profile. "
                "Other requests are not supported yet."
            }
        if state.get("error_code"):
            return {}
        try:
            return {"reply": explain(state["prompt"], state["evidence"])}
        except Exception:
            return {"error_code": "llm_unavailable"}

    graph = StateGraph(JobMatchingState)
    graph.add_node("retrieve_matches", retrieve)
    graph.add_node("explain_matches", explain_matches)
    graph.add_conditional_edges(START, route)
    graph.add_edge("retrieve_matches", "explain_matches")
    graph.add_edge("explain_matches", END)
    return graph.compile()
