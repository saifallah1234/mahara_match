import json
from collections.abc import Iterable
from typing import Any
from uuid import UUID

import pytest

from ai.agents.anetai import candidate_search_trace
from ai.tools import candidate_search
from backend.apps.recruitment.services.retrieval_scope import OfferSummary
from backend.common.exceptions import DomainNotFoundError

pytestmark = pytest.mark.unit

ACTOR: Any = object()
PYTHON, SQL = UUID(int=201), UUID(int=202)
PROFILES = [UUID(int=index) for index in range(1, 9)]
PRIVATE_TEXT = "Senior Python developer from Sfax, ex-ACME"


class FakeSearch:
    def documents(self) -> list[tuple[tuple[str, str], str]]:
        return [(("candidate_profile", str(pid)), f"python {PRIVATE_TEXT}") for pid in PROFILES]

    def nearest(self, vector: list[float], limit: int) -> list[tuple[str, str]]:
        return [("candidate_profile", str(PROFILES[0]))]

    def graph(self) -> list[tuple[str, str]]:
        return [("candidate_profile", str(PROFILES[0]))]


def _views(actor: object, ids: Iterable[UUID]) -> list[dict[str, Any]]:
    return [
        {
            "id": str(profile_id),
            "headline": PRIVATE_TEXT,
            "skills": ["Docker", "Python", "SQL"],
            "experience_titles": ["Engineer at ACME"],
            "education": [],
            "governorate": "Sfax",
            "work_mode": "REMOTE",
        }
        for profile_id in ids
    ]


@pytest.fixture
def calls(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    recorded: dict[str, Any] = {}

    def profile_search(actor: object, query: str, model: str, seeds: list[UUID]) -> FakeSearch:
        recorded["query"], recorded["seeds"] = query, seeds
        return FakeSearch()

    def offer(actor: object, offer_id: str) -> OfferSummary:
        if offer_id != "own":
            raise DomainNotFoundError()
        return OfferSummary(UUID(int=99), "Data Engineer", "Org", "", "DRAFT", {SQL: "SQL"})

    monkeypatch.setattr(candidate_search, "recruiter_profile_search", profile_search)
    monkeypatch.setattr(candidate_search, "limited_profile_view", _views)
    monkeypatch.setattr(candidate_search, "get_offer_summary", offer)
    return recorded


def test_returns_five_profile_ids_with_matched_skills(calls: dict[str, Any]) -> None:
    evidence = candidate_search.search_candidates(
        ACTOR, "candidates who know Python", embedder=lambda _: [1.0]
    )

    assert evidence["reason"] == "profiles_found"
    assert len(evidence["matches"]) == 5
    assert evidence["matches"][0] == {
        "profile_id": str(PROFILES[0]),
        "rank": 1,
        "leg_ranks": {"lexical": 1, "vector": 1, "graph": 1},
        "matched_skills": ["Python"],
    }
    assert calls["seeds"] == []


def test_offer_text_and_skills_become_the_query(calls: dict[str, Any]) -> None:
    evidence = candidate_search.search_candidates(
        ACTOR, "candidates for my offer", "own", embedder=lambda _: [1.0]
    )

    assert calls["seeds"] == [SQL]
    assert "Data Engineer" in calls["query"]
    assert evidence["matches"][0]["matched_skills"] == ["SQL"]


def test_foreign_or_unknown_offer_is_not_accessible(calls: dict[str, Any]) -> None:
    evidence = candidate_search.search_candidates(ACTOR, "candidates for offer X", "foreign")
    assert evidence == {"reason": "offer_not_accessible", "offer_id": None, "matches": []}
    assert "query" not in calls


def test_trace_contains_no_limited_profile_text(calls: dict[str, Any]) -> None:
    evidence = candidate_search.search_candidates(ACTOR, "python", embedder=lambda _: [1.0])
    evidence["matches"][0]["headline"] = PRIVATE_TEXT  # A future field must still be dropped.

    trace = json.dumps(candidate_search_trace(evidence))

    for private in (PRIVATE_TEXT, "Sfax", "ACME", "Docker", "REMOTE"):
        assert private not in trace
    assert str(PROFILES[0]) in trace
