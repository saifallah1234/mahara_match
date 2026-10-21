from decimal import Decimal

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from ai.llm.providers.embeddings import EmbeddingUnavailable
from backend.apps.assistant.models import AgentExecution, Conversation, ConversationMessage
from backend.apps.candidates.models import CandidateProfile, CandidateSkill, SkillLevel
from backend.apps.identity.models import Organization, Role, RoleCode, User, UserRole, UserStatus
from backend.apps.matching.models import OfferMatch
from backend.apps.matching.services.baseline import calculate_candidate_matches
from backend.apps.recruitment.models import JobOffer, JobOfferStatus, OfferSkill
from backend.apps.taxonomy.models import Skill

pytestmark = pytest.mark.django_db


def _ollama_down(_: str) -> list[float]:
    raise EmbeddingUnavailable("Ollama is not used by integration tests.")


def candidate(email: str = "candidate@example.com") -> User:
    user = User.objects.create_user(
        email, "test-password", first_name="Test", last_name="Candidate", status=UserStatus.ACTIVE
    )
    role, _ = Role.objects.get_or_create(code=RoleCode.CANDIDATE, defaults={"name": "Candidate"})
    UserRole.objects.create(user=user, role=role)
    CandidateProfile.objects.create(user=user)
    return user


def published_offer(owner: User, title: str = "Backend Engineer") -> tuple[JobOffer, Skill, Skill]:
    organization = Organization.objects.create(
        type="COMPANY",
        legal_name=f"{title} Ltd",
        matricule_fiscal="1234567A12345",
        verification_status="VERIFIED",
    )
    offer = JobOffer.objects.create(
        organization=organization,
        created_by=owner,
        title=title,
        description="Build useful software.",
        easy_apply=True,
        status=JobOfferStatus.PUBLISHED,
    )
    django = Skill.objects.create(canonical_name="Django")
    python = Skill.objects.create(canonical_name="Python")
    OfferSkill.objects.create(offer=offer, skill=django)
    OfferSkill.objects.create(offer=offer, skill=python)
    return offer, django, python


def test_calculator_persists_explainable_skill_coverage_and_updates_same_row() -> None:
    user = candidate()
    offer, django, python = published_offer(user)
    CandidateSkill.objects.create(
        candidate=user.candidate_profile, skill=django, level=SkillLevel.INTERMEDIATE
    )

    matches = calculate_candidate_matches(user)

    assert len(matches) == 1
    match = matches[0]
    assert match.offer_id == offer.id
    assert match.overall_score == Decimal("50.00")
    assert match.skill_score == Decimal("50.00")
    assert match.experience_score is None
    assert match.location_score is None
    assert match.explanation_json["matched_skills"] == ["Django"]
    assert match.explanation_json["missing_skills"] == ["Python"]
    assert match.explanation_json["offer_skills"] == ["Django", "Python"]

    CandidateSkill.objects.create(
        candidate=user.candidate_profile, skill=python, level=SkillLevel.BEGINNER
    )
    updated = calculate_candidate_matches(user)

    assert len(updated) == 1
    assert updated[0].id == match.id
    assert updated[0].overall_score == Decimal("100.00")
    assert OfferMatch.objects.filter(candidate=user.candidate_profile, offer=offer).count() == 1


def test_calculator_skips_unpublished_and_returns_no_scores_without_profile_skills() -> None:
    user = candidate()
    published_offer(user)
    assert calculate_candidate_matches(user) == []

    skill = Skill.objects.create(canonical_name="Rust")
    CandidateSkill.objects.create(
        candidate=user.candidate_profile, skill=skill, level=SkillLevel.ADVANCED
    )
    JobOffer.objects.filter(status=JobOfferStatus.PUBLISHED).update(status=JobOfferStatus.DRAFT)

    assert calculate_candidate_matches(user) == []
    assert OfferMatch.objects.count() == 0


def test_agent_run_persists_messages_execution_and_tool_evidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = candidate()
    offer, django, _ = published_offer(user)
    CandidateSkill.objects.create(
        candidate=user.candidate_profile, skill=django, level=SkillLevel.INTERMEDIATE
    )
    monkeypatch.setattr("ai.tools.job_search.embed_query", _ollama_down)
    monkeypatch.setattr(
        "ai.agents.anetai.explain_job_search",
        lambda prompt, evidence, language: "Top job: Backend Engineer.",
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("agent-run"), {"message": "What jobs match my profile?"}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    conversation = Conversation.objects.get(id=body["conversation_id"], user=user)
    execution = AgentExecution.objects.get(id=body["execution_id"])
    assert execution.status == "SUCCEEDED"
    assert execution.route == "candidate_job_search"
    assert execution.response_message.content == "Top job: Backend Engineer."
    assert execution.response_message.citations_json == [
        {"label": "Backend Engineer", "reference": f"offer:{offer.id}"}
    ]
    assert ConversationMessage.objects.filter(conversation=conversation).count() == 2
    tool_call = execution.tool_calls.get()
    assert tool_call.tool_name == "search_jobs_for_candidate"
    assert tool_call.status == "SUCCEEDED"
    assert tool_call.input_json == {"question": "What jobs match my profile?"}
    output = tool_call.output_summary_json
    assert output["vector_unavailable"] is True
    match = output["matches"][0]
    assert match["offer_id"] == str(offer.id)
    assert match["matched_skills"] == ["Django"]
    assert match["missing_skills"] == ["Python"]
    assert not OfferMatch.objects.exists()


def test_french_request_gets_a_french_template_without_the_llm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = candidate()
    offer, django, _ = published_offer(user)
    CandidateSkill.objects.create(
        candidate=user.candidate_profile, skill=django, level=SkillLevel.INTERMEDIATE
    )
    monkeypatch.setattr("ai.tools.job_search.embed_query", _ollama_down)
    monkeypatch.setattr(
        "ai.agents.anetai.get_chat_model", lambda: pytest.fail("French replies are templates.")
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("agent-run"),
        {"message": "Quels emplois correspondent à mon profil ?"},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["reply"] == (
        "1. Backend Engineer chez Backend Engineer Ltd. Compétences correspondantes : Django. "
        "Compétences manquantes : Python."
    )


def test_baseline_route_remains_selectable(monkeypatch: pytest.MonkeyPatch) -> None:
    user = candidate()
    offer, django, _ = published_offer(user)
    CandidateSkill.objects.create(
        candidate=user.candidate_profile, skill=django, level=SkillLevel.INTERMEDIATE
    )
    monkeypatch.setenv("ANETAI_CANDIDATE_TOOL", "baseline")
    monkeypatch.setattr(
        "ai.agents.anetai.explain_matches", lambda prompt, evidence: "Top job: Backend Engineer."
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("agent-run"), {"message": "What jobs match my profile?"}, format="json"
    )

    assert response.status_code == 200
    execution = AgentExecution.objects.get(id=response.json()["execution_id"])
    assert execution.route == "job_match_search"
    tool_call = execution.tool_calls.get()
    assert tool_call.tool_name == "get_candidate_job_matches"
    assert tool_call.output_summary_json["matches"][0]["offer_id"] == str(offer.id)


def test_agent_run_records_llm_failure_and_rejects_foreign_conversation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = candidate()
    other = candidate("other@example.com")
    foreign_conversation = Conversation.objects.create(user=other)
    monkeypatch.setattr("ai.tools.job_search.embed_query", _ollama_down)
    monkeypatch.setattr(
        "ai.agents.anetai.explain_job_search",
        lambda prompt, evidence, language: (_ for _ in ()).throw(RuntimeError()),
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("agent-run"), {"message": "What jobs match my profile?"}, format="json"
    )

    assert response.status_code == 503
    error = response.json()["error"]
    assert error["code"] == "llm_unavailable"
    execution = AgentExecution.objects.get(id=error["details"]["execution_id"])
    assert execution.status == "FAILED"
    assert execution.error_code == "llm_unavailable"
    assert execution.response_message is None
    assert execution.tool_calls.get().status == "SUCCEEDED"
    assert ConversationMessage.objects.filter(conversation__user=user).count() == 1

    foreign_response = client.post(
        reverse("agent-run"),
        {"message": "What jobs match my profile?", "conversation_id": str(foreign_conversation.id)},
        format="json",
    )
    assert foreign_response.status_code == 404


def test_agent_run_requires_authentication_and_candidate_profile() -> None:
    client = APIClient()
    assert (
        client.post(reverse("agent-run"), {"message": "match me"}, format="json").status_code == 401
    )

    user = User.objects.create_user(
        "recruiter@example.com",
        "test-password",
        first_name="Test",
        last_name="Recruiter",
        status=UserStatus.ACTIVE,
    )
    client.force_authenticate(user)
    response = client.post(reverse("agent-run"), {"message": "match me"}, format="json")
    assert response.status_code == 403
    assert Conversation.objects.count() == 0


def test_unsupported_request_is_persisted_without_calling_matching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = candidate()
    monkeypatch.setattr(
        "ai.agents.anetai.search_jobs_for_candidate",
        lambda *_: pytest.fail("Unsupported requests must not call matching."),
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        reverse("agent-run"), {"message": "Can you improve my CV?"}, format="json"
    )

    assert response.status_code == 200
    body = response.json()
    execution = AgentExecution.objects.get(id=body["execution_id"])
    assert execution.route == "unsupported"
    assert execution.status == "SUCCEEDED"
    assert execution.tool_calls.count() == 0
    assert "not supported yet" in body["reply"]
    assert ConversationMessage.objects.filter(conversation_id=body["conversation_id"]).count() == 2
