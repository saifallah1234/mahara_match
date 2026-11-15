"""Recruiter runs through the agent endpoint: scope, offer references and trace privacy."""

import json
from typing import Any
from uuid import uuid4

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from ai.llm.providers.embeddings import EmbeddingUnavailable
from backend.apps.assistant.models import AgentExecution, ConversationMessage
from backend.apps.candidates.models import CandidateSkill, ProfileVisibility, SkillLevel
from backend.apps.recruitment.models import JobOffer, OfferSkill
from backend.apps.taxonomy.models import Skill

pytestmark = [pytest.mark.integration, pytest.mark.django_db]

HEADLINE = "Kotlin mobile developer with a private-looking headline"


def _ollama_down(_: str) -> list[float]:
    raise EmbeddingUnavailable("Ollama is not used by integration tests.")


@pytest.fixture
def world(phase3: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    monkeypatch.setattr("ai.tools.candidate_search.embed_query", _ollama_down)
    kotlin = Skill.objects.create(canonical_name="Kotlin")
    visible = phase3["candidate_profile"]
    visible.profile_visibility = ProfileVisibility.RECRUITERS
    visible.headline = HEADLINE
    visible.governorate = "Sfax"
    visible.save()
    hidden = phase3["other_candidate_profile"]
    hidden.profile_visibility = ProfileVisibility.PRIVATE
    hidden.headline = "Kotlin developer"
    hidden.save()
    for profile in (visible, hidden):
        CandidateSkill.objects.create(candidate=profile, skill=kotlin, level=SkillLevel.EXPERT)

    def offer(owner: str, title: str, status: str) -> JobOffer:
        created = JobOffer.objects.create(
            organization=phase3[f"{owner}_org"],
            created_by=phase3[owner],
            title=title,
            description="Mobile apps",
            easy_apply=True,
            status=status,
        )
        OfferSkill.objects.create(offer=created, skill=kotlin)
        return created

    own_draft = offer("recruiter", "Android Engineer", "DRAFT")
    foreign = offer("other_recruiter", "Mobile Lead", "PUBLISHED")
    return {**phase3, "own_draft": own_draft, "foreign": foreign}


def _run(user: Any, message: str) -> Any:
    client = APIClient()
    client.force_authenticate(user)
    return client.post(reverse("agent-run"), {"message": message}, format="json")


def test_recruiter_finds_only_opted_in_profiles_and_trace_holds_ids_and_skills(
    world: dict[str, Any],
) -> None:
    response = _run(world["recruiter"], "Find candidates who know Kotlin")

    assert response.status_code == 200
    body = response.json()
    visible_id = str(world["candidate_profile"].id)
    hidden_id = str(world["other_candidate_profile"].id)
    assert body["reply"].startswith("Profile 1. Matched skills: Kotlin.")
    citations = ConversationMessage.objects.get(id=body["message_id"]).citations_json
    assert citations == [{"label": "Profil n°1", "reference": f"candidate_profile:{visible_id}"}]
    assert hidden_id not in json.dumps(citations)
    execution = AgentExecution.objects.get(id=body["execution_id"])
    assert execution.route == "recruiter_candidate_search"
    tool_call = execution.tool_calls.get()
    assert tool_call.tool_name == "search_candidates"
    assert tool_call.output_summary_json["matches"] == [
        {
            "profile_id": visible_id,
            "rank": 1,
            "leg_ranks": tool_call.output_summary_json["matches"][0]["leg_ranks"],
            "matched_skills": ["Kotlin"],
        }
    ]
    stored = json.dumps(tool_call.output_summary_json) + " ".join(
        ConversationMessage.objects.filter(conversation_id=body["conversation_id"]).values_list(
            "content", flat=True
        )
    )
    for private in (HEADLINE, "Sfax", "Private", "Identity", "candidate@example.test"):
        assert private not in stored


def test_candidates_for_own_draft_offer_use_its_skills(world: dict[str, Any]) -> None:
    response = _run(world["recruiter"], "Which candidates fit my offer Android Engineer?")

    assert response.status_code == 200
    tool_call = AgentExecution.objects.get(id=response.json()["execution_id"]).tool_calls.get()
    assert tool_call.output_summary_json["offer_id"] == str(world["own_draft"].id)
    assert tool_call.output_summary_json["matches"][0]["matched_skills"] == ["Kotlin"]


@pytest.mark.parametrize("which", ["foreign", "unknown"])
def test_offer_outside_scope_is_not_accessible_without_leaking_existence(
    world: dict[str, Any], which: str
) -> None:
    offer_id = world["foreign"].id if which == "foreign" else uuid4()

    response = _run(world["recruiter"], f"Find candidates for offer {offer_id}")

    assert response.status_code == 200
    assert response.json()["reply"] == "This offer is not accessible from your account."


def test_recruiter_searches_own_offers_including_drafts(world: dict[str, Any]) -> None:
    response = _run(world["recruiter"], "Show my offers about Kotlin")

    assert response.status_code == 200
    reply = response.json()["reply"]
    assert reply == "1. Android Engineer (draft). Skills: Kotlin."
    assert "Mobile Lead" not in reply


def test_unverified_recruiter_and_other_roles_are_refused(world: dict[str, Any]) -> None:
    organization = world["recruiter_org"]
    organization.verification_status = "PENDING"
    organization.save()

    for user in (world["recruiter"], world["admin"], world["provider"]):
        assert _run(user, "Find candidates who know Kotlin").status_code == 403


def test_candidate_cannot_use_recruiter_intents(world: dict[str, Any]) -> None:
    response = _run(world["candidate"], "Find candidates who know Kotlin")

    assert response.status_code == 200
    execution = AgentExecution.objects.get(id=response.json()["execution_id"])
    assert execution.route == "unsupported"
    assert execution.tool_calls.count() == 0
