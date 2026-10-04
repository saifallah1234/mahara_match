import os

import pytest

from ai.agents.anetai import _stays_within_evidence, explain_matches
from ai.workflows.job_matching import build_job_matching_graph

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
    graph = build_job_matching_graph(lambda _: evidence, explain_matches)

    result = graph.invoke(
        {"actor": object(), "prompt": "What jobs match my profile?", "supported": True}
    )

    assert result["tool_call"]["status"] == "SUCCEEDED"
    assert result["reply"]
    assert _stays_within_evidence(result["reply"], evidence)
    assert "75" in result["reply"]
