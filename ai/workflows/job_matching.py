from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class AgentState(TypedDict, total=False):
    actor: Any
    prompt: str
    route: str
    language: str
    evidence: dict[str, Any]
    reply: str
    error_code: str
    tool_call: dict[str, Any]


def _whole(evidence: dict[str, Any]) -> dict[str, Any]:
    return evidence


@dataclass(frozen=True)
class RouteSpec:
    """One supported route: the tool it calls and how its evidence becomes a reply."""

    tool_name: str
    tool: Callable[[Any, str], dict[str, Any]]
    explain: Callable[[str, dict[str, Any], str], str]
    tool_input: Callable[[str], dict[str, Any]] = field(default=lambda prompt: {})
    # What the tool-call record may keep; recruiter routes drop profile text here.
    trace: Callable[[dict[str, Any]], dict[str, Any]] = _whole


def build_agent_graph(
    routes: Mapping[str, RouteSpec], unsupported_reply: Callable[[str], str]
) -> Any:
    def route(state: AgentState) -> str:
        return "call_tool" if state["route"] in routes else "explain"

    def call_tool(state: AgentState) -> dict[str, Any]:
        spec = routes[state["route"]]
        started = monotonic()
        tool_input = spec.tool_input(state["prompt"])
        try:
            evidence = spec.tool(state["actor"], state["prompt"])
        except Exception:
            return {
                "error_code": "matching_failed",
                "tool_call": {
                    "tool_name": spec.tool_name,
                    "input": tool_input,
                    "output": {},
                    "status": "FAILED",
                    "latency_ms": int((monotonic() - started) * 1000),
                    "error_code": "matching_failed",
                },
            }
        return {
            "evidence": evidence,
            "tool_call": {
                "tool_name": spec.tool_name,
                "input": tool_input,
                "output": spec.trace(evidence),
                "status": "SUCCEEDED",
                "latency_ms": int((monotonic() - started) * 1000),
                "error_code": "",
            },
        }

    def explain(state: AgentState) -> dict[str, str]:
        spec = routes.get(state["route"])
        if spec is None:
            return {"reply": unsupported_reply(state.get("language", "en"))}
        if state.get("error_code"):
            return {}
        try:
            return {
                "reply": spec.explain(
                    state["prompt"], state["evidence"], state.get("language", "en")
                )
            }
        except Exception:
            return {"error_code": "llm_unavailable"}

    graph = StateGraph(AgentState)
    graph.add_node("call_tool", call_tool)
    graph.add_node("explain", explain)
    graph.add_conditional_edges(START, route)
    graph.add_edge("call_tool", "explain")
    graph.add_edge("explain", END)
    return graph.compile()
