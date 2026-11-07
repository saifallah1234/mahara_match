# Placement: tests/integration/identity/test_seed_demo.py
from datetime import date
from io import StringIO

import pytest
from django.apps import apps
from django.conf import settings as django_settings
from django.core.management import CommandError, call_command
from django.urls import reverse
from rest_framework.test import APIClient

from ai.llm.providers.embeddings import EmbeddingUnavailable
from backend.apps.assistant.models import AgentExecution
from backend.apps.candidates.models import CV, CandidateProfile, CandidateSkill
from backend.apps.documents.models import Document
from backend.apps.identity.models import User, UserRole
from backend.apps.imports.models import DataSource, ImportBatch
from backend.apps.recruitment.models import Application, JobOffer
from backend.apps.training.models import TrainingEnrollment, TrainingProgram

pytestmark = pytest.mark.django_db

PASSWORD = "Demo-Password-2026!"
DOMAIN = "demo.mahara.test"


@pytest.fixture
def debug_on(settings):
    settings.DEBUG = True


def seed() -> str:
    out = StringIO()
    call_command("seed_demo", password=PASSWORD, stdout=out)
    return out.getvalue()


def signed_in(email: str) -> APIClient:
    client = APIClient(enforce_csrf_checks=True)
    assert client.get(reverse("csrf-cookie")).status_code == 204
    login = client.post(
        reverse("token-obtain-pair"),
        {"email": email, "password": PASSWORD},
        format="json",
        HTTP_X_CSRFTOKEN=client.cookies[django_settings.CSRF_COOKIE_NAME].value,
    )
    assert login.status_code == 200, login.content
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.json()['access']}")
    return client


def workspaces(email: str) -> list[tuple[str, str | None]]:
    client = signed_in(email)
    return [
        (item["role_code"], item["organization"] and item["organization"]["type"])
        for item in client.get(reverse("user-me")).json()["workspaces"]
    ]


def test_every_seeded_account_signs_in_to_its_workspace(debug_on) -> None:
    output = seed()

    expected = {
        f"admin@{DOMAIN}": [("ADMIN", None)],
        f"ministere@{DOMAIN}": [("MINISTRY_MANAGER", "MINISTRY")],
        f"recruteur@{DOMAIN}": [("RECRUITER", "COMPANY")],
        f"formation@{DOMAIN}": [("TRAINING_MANAGER", "TRAINING_PROVIDER")],
        f"candidat@{DOMAIN}": [("CANDIDATE", None)],
        f"candidat2@{DOMAIN}": [("CANDIDATE", None)],
    }
    for email, workspace in expected.items():
        assert workspaces(email) == workspace
        assert email in output
    assert PASSWORD not in output


def test_skills_come_from_esco_and_education_levels_are_ordered(debug_on) -> None:
    seed()
    client = signed_in(f"candidat@{DOMAIN}")

    skills = client.get(reverse("skill-list"), {"page_size": 100}).json()["results"]
    python = next(s for s in skills if s["canonical_name"] == "Python (computer programming)")
    assert python["category"] == "knowledge"
    assert python["description"].endswith(
        "\nESCO: http://data.europa.eu/esco/skill/ccd0a1d9-afda-43d9-b901-96344886e14d"
    )
    levels = client.get(reverse("education-level-list")).json()["results"]
    assert [level["name"] for level in levels] == [
        "Baccalauréat",
        "Licence",
        "Diplôme d'ingénieur",
        "Master",
        "Doctorat",
    ]


def row_counts() -> dict[str, int]:
    return {model._meta.label: model._default_manager.count() for model in apps.get_models()}


def test_a_second_run_adds_nothing(debug_on) -> None:
    seed()
    before = row_counts()
    seed()
    assert row_counts() == before


def test_an_existing_account_is_left_unchanged(debug_on) -> None:
    existing = User.objects.create_user(
        f"candidat@{DOMAIN}", "Earlier-Password-1!", first_name="Earlier", last_name="Owner"
    )

    seed()

    existing.refresh_from_db()
    assert (existing.first_name, existing.status) == ("Earlier", "PENDING")
    assert existing.check_password("Earlier-Password-1!")
    assert not UserRole.objects.filter(user=existing).exists()
    assert not hasattr(existing, "candidate_profile")


def test_refuses_to_run_without_debug(settings) -> None:
    settings.DEBUG = False
    with pytest.raises(CommandError, match="DEBUG"):
        seed()
    assert not User.objects.exists()


def _ollama_down(_: str) -> list[float]:
    raise EmbeddingUnavailable("Ollama is not used by integration tests.")


def test_main_candidate_gets_seeded_offers_with_skills_and_training(
    debug_on, monkeypatch: pytest.MonkeyPatch
) -> None:
    seed()
    monkeypatch.setattr("ai.tools.job_search.embed_query", _ollama_down)
    client = signed_in(f"candidat@{DOMAIN}")

    response = client.post(
        reverse("agent-run"),
        {"message": "Quelles offres d'emploi me correspondent ?"},
        format="json",
    )

    assert response.status_code == 200, response.content
    execution = AgentExecution.objects.get(id=response.json()["execution_id"])
    matches = execution.tool_calls.get().output_summary_json["matches"]
    seeded = set(
        JobOffer.objects.filter(
            organization__registration_number="DEMO-COMPANY", status="PUBLISHED"
        ).values_list("title", flat=True)
    )
    explained = [
        m for m in matches if m["title"] in seeded and m["matched_skills"] and m["missing_skills"]
    ]
    assert explained
    assert any(m["training"] for m in explained)
    reply = response.json()["reply"]
    assert "Compétences manquantes" in reply
    assert "Formations pour les compétences manquantes" in reply


def test_recruiter_discovers_both_seeded_candidates(debug_on) -> None:
    seed()
    client = signed_in(f"recruteur@{DOMAIN}")

    profiles = client.get(reverse("candidate-profile-list")).json()["results"]

    seeded = CandidateProfile.objects.filter(
        user__email__in=[f"candidat@{DOMAIN}", f"candidat2@{DOMAIN}"]
    ).values_list("id", flat=True)
    assert {str(profile_id) for profile_id in seeded} <= {p["id"] for p in profiles}
    assert len(seeded) == 2


def test_scenario_offers_programs_and_sessions(debug_on) -> None:
    output = seed()

    offers = JobOffer.objects.filter(organization__registration_number="DEMO-COMPANY")
    published = offers.filter(status="PUBLISHED")
    assert published.count() == 4
    assert offers.filter(status="DRAFT").count() == 1
    assert len(set(published.values_list("governorate", flat=True))) >= 3
    for offer in published:
        assert offer.easy_apply
        assert offer.application_deadline > date(2026, 11, 8)
        flags = set(offer.offer_skills.values_list("is_mandatory", flat=True))
        assert flags == {True, False}
    programs = TrainingProgram.objects.filter(organization__registration_number="DEMO-TRAINING")
    assert 2 <= programs.filter(status="ACTIVE").count() <= 3
    for program in programs:
        session = program.sessions.get()
        assert session.registration_deadline.date() > date(2026, 11, 8)
        assert session.start_date.date() > date(2026, 11, 8)
    for model in (Application, CV, Document, TrainingEnrollment, ImportBatch):
        assert not model.objects.exists()
    assert not DataSource.objects.filter(is_authorized=True).exists()
    assert "index_retrieval --schema public" in output
    assert "Tanitjobs" in output


def test_candidates_seeded_without_skills_get_them_on_the_next_run(debug_on) -> None:
    seed()
    CandidateSkill.objects.all().delete()

    seed()

    main = CandidateSkill.objects.filter(candidate__user__email=f"candidat@{DOMAIN}")
    assert set(main.values_list("skill__canonical_name", "level")) >= {
        ("Python (computer programming)", "ADVANCED"),
        ("SQL", "INTERMEDIATE"),
    }


def test_seeded_ministry_manager_reads_indicators_across_governorates(debug_on) -> None:
    seed()

    response = signed_in(f"ministere@{DOMAIN}").get("/api/v1/reporting/indicators/")

    assert response.status_code == 200
    regions = [row for row in response.json()["regions"] if row["offers"]]
    assert len(regions) >= 3
