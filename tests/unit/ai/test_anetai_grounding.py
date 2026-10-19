from types import SimpleNamespace
from typing import Any

import pytest

from ai.agents.anetai import explain_matches
from ai.agents.templates import unsupported_reply
from ai.workflows.job_matching import RouteSpec, build_agent_graph

pytestmark = pytest.mark.unit


class StubModel:
    def __init__(self, content: str) -> None:
        self.content = content

    def invoke(self, messages: list[Any]) -> SimpleNamespace:
        return SimpleNamespace(content=self.content)


def test_unsafe_ollama_claims_fall_back_to_match_evidence(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "ai.agents.anetai.get_chat_model",
        lambda: StubModel("You have all required skills. Apply here: http://link.com/apply."),
    )
    evidence = {
        "reason": "matches_found",
        "matches": [
            {
                "title": "Python Developer",
                "organization": "Example Org",
                "score": "100.00",
                "matched_skills": ["Python"],
                "missing_skills": [],
                "offer_skills": ["Python"],
                "offer_url": "",
            }
        ],
    }

    reply = explain_matches("What jobs match my profile?", evidence)

    assert reply == (
        "Python Developer at Example Org: 100.00% skill coverage. "
        "Matched skills: Python. Missing skills: none."
    )


def test_grounded_ollama_explanation_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = (
        "Python Developer at Example Org has 100% skill coverage. Matched: Python; missing: none."
    )
    monkeypatch.setattr("ai.agents.anetai.get_chat_model", lambda: StubModel(reply))
    evidence = {
        "reason": "matches_found",
        "matches": [
            {
                "title": "Python Developer",
                "organization": "Example Org",
                "score": "100.00",
                "matched_skills": ["Python"],
                "missing_skills": [],
                "offer_skills": ["Python"],
                "offer_url": "",
            }
        ],
    }

    assert explain_matches("What jobs match my profile?", evidence) == reply


def test_empty_results_use_evidence_summary_without_calling_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ai.agents.anetai.get_chat_model",
        lambda: pytest.fail("No LLM call is needed when there are no scored matches."),
    )

    reply = explain_matches(
        "What jobs match my profile?",
        {"reason": "candidate_has_no_skills", "matches": []},
    )

    assert "Add skills to your profile" in reply


def test_unsupported_graph_path_does_not_call_matching_or_model() -> None:
    route = RouteSpec(
        tool_name="never",
        tool=lambda *_: pytest.fail("Unsupported requests must not call matching."),
        explain=lambda *_: pytest.fail("Unsupported requests do not need model wording."),
    )
    graph = build_agent_graph({"candidate_job_search": route}, unsupported_reply)

    result = graph.invoke(
        {
            "actor": object(),
            "prompt": "Can you improve my CV?",
            "route": "unsupported",
            "language": "en",
        }
    )

    assert "not supported yet" in result["reply"]
    assert "tool_call" not in result


@pytest.mark.parametrize(
    "reply",
    [
        "Python Developer at Example Org: 80% skill coverage. Matched: Python. Missing: none.",
        "Python Developer at Example Org: 100% skill coverage. Matched: Python. Missing: none. "
        "This role requires five years of experience.",
        "Python Developer at Example Org: 100% skill coverage. Matched: Python. Missing: none. "
        "https://invented.example/job",
        "Python Developer at Example Org: 100% skill coverage. Matched: Python. Missing: none. "
        "This remote role is based in Tunis.",
    ],
)
def test_changed_score_or_unsupported_claims_use_deterministic_fallback(
    monkeypatch: pytest.MonkeyPatch, reply: str
) -> None:
    monkeypatch.setattr("ai.agents.anetai.get_chat_model", lambda: StubModel(reply))
    evidence = {
        "reason": "matches_found",
        "matches": [
            {
                "title": "Python Developer",
                "organization": "Example Org",
                "score": "100.00",
                "matched_skills": ["Python"],
                "missing_skills": [],
                "offer_skills": ["Python"],
                "offer_url": "",
            }
        ],
    }

    assert explain_matches("What jobs match my profile?", evidence) == (
        "Python Developer at Example Org: 100.00% skill coverage. "
        "Matched skills: Python. Missing skills: none."
    )
