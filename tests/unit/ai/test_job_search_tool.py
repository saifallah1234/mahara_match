from collections.abc import Iterable
from types import SimpleNamespace
from typing import Any
from uuid import UUID

import pytest

from ai.agents.anetai import explain_job_search
from ai.llm.providers.embeddings import EmbeddingUnavailable
from ai.tools import job_search
from backend.apps.recruitment.services.retrieval_scope import OfferSummary

pytestmark = pytest.mark.unit

PYTHON, SQL, DOCKER = UUID(int=101), UUID(int=102), UUID(int=103)
OFFERS = [UUID(int=index) for index in range(1, 8)]
ACTOR: Any = object()


class FakeSearch:
    def __init__(self, profile_skill_ids: list[UUID]) -> None:
        self.profile_skill_ids = profile_skill_ids

    def documents(self) -> list[tuple[tuple[str, str], str]]:
        return [(("offer", str(offer_id)), "python developer") for offer_id in OFFERS]

    def nearest(self, vector: list[float], limit: int) -> list[tuple[str, str]]:
        return [("offer", str(OFFERS[0]))]

    def graph(self) -> list[tuple[str, str]]:
        return [("offer", str(OFFERS[0]))]


def _summaries(_: object, offer_ids: Iterable[UUID]) -> list[OfferSummary]:
    return [
        OfferSummary(
            offer_id=offer_id,
            title=f"Offer {offer_id.int}",
            organization="Org",
            offer_url="",
            status="PUBLISHED",
            skills={PYTHON: "Python", SQL: "SQL", DOCKER: "Docker"},
        )
        for offer_id in offer_ids
    ]


@pytest.fixture
def services(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    calls: dict[str, Any] = {"training": []}

    def training(missing: list[UUID], limit: int) -> list[dict[str, str]]:
        calls["training"].append((missing, limit))
        return [
            {
                "program_id": f"p{index}",
                "title": f"Course {index}",
                "organization": "A",
                "skill": "x",
            }
            for index in range(limit)
        ]

    calls["search"] = FakeSearch([PYTHON])
    monkeypatch.setattr(job_search, "candidate_offer_search", lambda *_: calls["search"])
    monkeypatch.setattr(job_search, "visible_offers", lambda actor: "scope")
    monkeypatch.setattr(job_search, "offer_summaries", _summaries)
    monkeypatch.setattr(job_search, "training_for_missing_skills", training)
    return calls


def test_returns_five_offers_with_skill_split_and_two_trainings(services: dict[str, Any]) -> None:
    evidence = job_search.search_jobs_for_candidate(ACTOR, "python", embedder=lambda _: [1.0])

    assert evidence["reason"] == "matches_found"
    assert len(evidence["matches"]) == 5
    first = evidence["matches"][0]
    assert first["offer_id"] == str(OFFERS[0])
    assert first["rank"] == 1
    assert first["leg_ranks"] == {"lexical": 1, "vector": 1, "graph": 1}
    assert first["matched_skills"] == ["Python"]
    assert first["missing_skills"] == ["SQL", "Docker"]
    assert all(len(match["training"]) <= 2 for match in evidence["matches"])
    assert services["training"][0] == ([SQL, DOCKER], 2)
    assert not evidence["vector_unavailable"]


def test_embedding_outage_is_reported_not_raised(services: dict[str, Any]) -> None:
    def down(_: str) -> list[float]:
        raise EmbeddingUnavailable("refused")

    evidence = job_search.search_jobs_for_candidate(ACTOR, "python", embedder=down)

    assert evidence["vector_unavailable"]
    assert evidence["matches"]


def test_reason_codes_for_empty_results(services: dict[str, Any]) -> None:
    services["search"] = SimpleNamespace(
        profile_skill_ids=[],
        documents=lambda: [],
        nearest=lambda vector, limit: [],
        graph=lambda: [],
    )
    evidence = job_search.search_jobs_for_candidate(ACTOR, "xyz", embedder=lambda _: [1.0])
    assert evidence["reason"] == "candidate_has_no_skills"
    assert not evidence["profile_has_skills"]

    services["search"].profile_skill_ids = [PYTHON]
    evidence = job_search.search_jobs_for_candidate(ACTOR, "xyz", embedder=lambda _: [1.0])
    assert evidence["reason"] == "no_matching_offers"


def _grounding_evidence() -> dict[str, Any]:
    return {
        "reason": "matches_found",
        "profile_has_skills": True,
        "matches": [
            {
                "title": "Data Analyst",
                "organization": "Org",
                "offer_url": "",
                "matched_skills": ["SQL"],
                "missing_skills": ["Python"],
                "offer_skills": ["Python", "SQL"],
                "training": [
                    {
                        "program_id": "p",
                        "title": "Python 101",
                        "organization": "A",
                        "skill": "Python",
                    }
                ],
            }
        ],
    }


class StubModel:
    def __init__(self, content: str) -> None:
        self.content = content

    def invoke(self, messages: list[Any]) -> SimpleNamespace:
        return SimpleNamespace(content=self.content)


def test_grounded_english_rewording_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    reply = (
        "Data Analyst at Org: matched skills SQL, missing skills Python. "
        "Training for missing skills: Python 101."
    )
    monkeypatch.setattr("ai.agents.anetai.get_chat_model", lambda: StubModel(reply))
    assert explain_job_search("Find jobs", _grounding_evidence(), "en") == reply


@pytest.mark.parametrize(
    "reply",
    [
        "Data Analyst at Org is a 90% match. Matched skills: SQL. Missing skills: Python. "
        "Training: Python 101.",
        "Data Analyst at Org. Matched skills: SQL. Missing skills: Python.",
        "Data Analyst at Org. Matched skills: SQL. Missing skills: Python. Training: Python 101. "
        "You are qualified.",
    ],
)
def test_ungrounded_rewording_falls_back_to_template(
    monkeypatch: pytest.MonkeyPatch, reply: str
) -> None:
    monkeypatch.setattr("ai.agents.anetai.get_chat_model", lambda: StubModel(reply))
    assert explain_job_search("Find jobs", _grounding_evidence(), "en").startswith(
        "1. Data Analyst at Org. Matched skills: SQL."
    )


@pytest.mark.parametrize("language", ["fr", "ar"])
def test_french_and_arabic_never_call_the_model(
    monkeypatch: pytest.MonkeyPatch, language: str
) -> None:
    monkeypatch.setattr(
        "ai.agents.anetai.get_chat_model", lambda: pytest.fail("FR/AR replies are templates.")
    )
    assert "Data Analyst" in explain_job_search("q", _grounding_evidence(), language)
