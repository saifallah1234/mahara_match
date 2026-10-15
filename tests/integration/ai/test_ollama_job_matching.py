import os

import pytest

from ai.agents.anetai import (
    _stays_within_evidence,
    _stays_within_search_evidence,
    explain_job_search,
    explain_matches,
)
from ai.agents.templates import job_search_reply, unsupported_reply
from ai.workflows.job_matching import RouteSpec, build_agent_graph

pytestmark = [
    pytest.mark.integration,
    pytest.mark.ollama,
    pytest.mark.skipif(
        os.getenv("RUN_OLLAMA_TESTS") != "1",
        reason="Set RUN_OLLAMA_TESTS=1 to run against the real Ollama service.",
    ),
]


def test_job_matching_graph_with_real_ollama() -> None:
    evidence = {
        "reason": "matches_found",
        "matches": [
            {
                "offer_id": "synthetic-offer-1",
                "title": "Python Developer",
                "organization": "Synthetic Example Org",
                "score": "75.00",
                "matched_skills": ["Python", "Django"],
                "missing_skills": ["PostgreSQL"],
                "offer_skills": ["Python", "Django", "PostgreSQL"],
                "offer_url": "https://jobs.example.test/python-developer",
            }
        ],
    }
    route = RouteSpec(
        tool_name="get_candidate_job_matches",
        tool=lambda *_: evidence,
        explain=lambda prompt, found, language: explain_matches(prompt, found),
    )
    graph = build_agent_graph({"job_match_search": route}, unsupported_reply)

    result = graph.invoke(
        {
            "actor": object(),
            "prompt": "What jobs match my profile?",
            "route": "job_match_search",
            "language": "en",
        }
    )

    assert result["tool_call"]["status"] == "SUCCEEDED"
    assert result["reply"]
    assert _stays_within_evidence(result["reply"], evidence)
    assert "75" in result["reply"]


def test_job_search_explanation_with_real_ollama() -> None:
    evidence = {
        "reason": "matches_found",
        "profile_has_skills": True,
        "vector_unavailable": False,
        "matches": [
            {
                "offer_id": "synthetic-offer-1",
                "rank": 1,
                "leg_ranks": {"lexical": 1, "vector": 2, "graph": 1},
                "title": "Python Developer",
                "organization": "Synthetic Example Org",
                "offer_url": "https://jobs.example.test/python-developer",
                "matched_skills": ["Python", "Django"],
                "missing_skills": ["PostgreSQL"],
                "offer_skills": ["Django", "PostgreSQL", "Python"],
                "training": [
                    {
                        "program_id": "synthetic-program-1",
                        "title": "SQL Foundations",
                        "organization": "Synthetic Academy",
                        "skill": "PostgreSQL",
                    }
                ],
            }
        ],
    }

    reply = explain_job_search("Find jobs for me", evidence, "en")

    assert reply
    assert reply == job_search_reply(evidence, "en") or _stays_within_search_evidence(
        reply, evidence
    )
