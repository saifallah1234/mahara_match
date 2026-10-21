# Placement: tests/unit/ai/test_agent_citations.py
import pytest

from ai.agents.service import citations_for

pytestmark = pytest.mark.unit


def test_offer_match_cites_its_offer_and_training_programs_once() -> None:
    evidence = {
        "matches": [
            {
                "offer_id": "o1",
                "title": "Backend Engineer",
                "training": [{"program_id": "p1", "title": "Django course"}],
            },
            {
                "offer_id": "o2",
                "title": "Data Analyst",
                "training": [{"program_id": "p1", "title": "Django course"}],
            },
        ]
    }

    assert citations_for(evidence) == [
        {"label": "Backend Engineer", "reference": "offer:o1"},
        {"label": "Django course", "reference": "program:p1"},
        {"label": "Data Analyst", "reference": "offer:o2"},
    ]


def test_profile_match_cites_its_rank_not_its_name() -> None:
    evidence = {"matches": [{"profile_id": "c1", "rank": 2, "matched_skills": ["Python"]}]}

    assert citations_for(evidence) == [{"label": "Profil n°2", "reference": "candidate_profile:c1"}]


@pytest.mark.parametrize("evidence", [{}, {"reason": "no_matching_offers", "matches": []}])
def test_reply_without_matches_cites_nothing(evidence: dict[str, object]) -> None:
    assert citations_for(evidence) == []
