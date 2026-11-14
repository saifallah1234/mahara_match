# Placement: tests/integration/candidates/test_cv_parsing.py
"""CV analysis: start, background run (fake LLM, real PDF text), proposal, confirmed apply."""

from hashlib import sha256
from typing import Any
from uuid import UUID

import django.db
import pymupdf
import pytest
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient

from ai.document_intelligence.parsing import cv_schema as s
from backend.apps.candidates.models import (
    CV,
    CandidateLanguage,
    CandidateSkill,
    Education,
    Experience,
    Project,
)
from backend.apps.candidates.services import cv_parsing
from backend.apps.documents.models import Document
from backend.apps.taxonomy.models import EducationLevel, Language, Skill
from pipelines.document_processing import cv_parsing as pipeline

pytestmark = pytest.mark.integration


def _pdf(text: str) -> bytes:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), text, fontsize=11)
    return document.tobytes()


@pytest.fixture
def spawned(monkeypatch: pytest.MonkeyPatch) -> list[UUID]:
    calls: list[UUID] = []
    monkeypatch.setattr(cv_parsing, "_spawn", calls.append)
    return calls


@pytest.fixture
def cv(phase3: dict[str, Any]) -> CV:
    call_command("seed_languages", verbosity=0)
    call_command("seed_education_levels", verbosity=0)
    content = _pdf("Yasmine Chakroun - Ariana, Tunis - Python, Odoo")
    user = phase3["candidate"]
    document = Document.objects.create(
        owner_user=user,
        type="CV",
        storage_uri=f"documents/{user.id}/cv-1",
        file_name="cv.pdf",
        mime_type="application/pdf",
        size_bytes=len(content),
        checksum=sha256(content).hexdigest(),
        scan_status="PENDING",
        uploaded_at=timezone.now(),
    )
    return CV.objects.create(
        candidate=phase3["candidate_profile"], document=document, title="CV", version_number=1
    )


def _client(user: Any) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


class FakeLLM:
    """Answers each section schema with fixed values, like a provider would."""

    used = ["fake"]

    def generate_structured(self, system: str, user: str, schema: type[Any]) -> Any:
        assert "Python" in user  # the PDF text reached the prompt
        answers: dict[type[Any], Any] = {
            s.PersonalInfoAndSummary: s.PersonalInfoAndSummary(
                personal_information=s.PersonalInformation(
                    full_name="Yasmine Chakroun",
                    email="y@example.test",
                    phone="+216 24 305 500",
                    location="Ariana, Tunis",
                    linkedin=None,
                    github=None,
                ),
                headline="Étudiante en Génie Logiciel",
                professional_summary=None,
            ),
            s.EducationList: s.EducationList(
                education=[
                    s.Education(
                        degree="Diplôme d'Ingénieur en Génie Logiciel",
                        degree_level=s.DegreeLevel.MASTER,
                        institution="FSB",
                        field_of_study="Génie Logiciel",
                        start_date="Sept. 2024",
                        end_date="Present",
                        is_current=True,
                        description=None,
                    )
                ]
            ),
            s.ExperienceList: s.ExperienceList(
                experience=[
                    s.Experience(
                        job_title="Stagiaire",
                        company="OneTech",
                        location=None,
                        employment_type="Stage",
                        start_date="Juillet 2025",
                        end_date="Août 2025",
                        description=None,
                        responsibilities=["Migration de modules Odoo"],
                        technologies=["Odoo", "Python"],
                    )
                ]
            ),
            s.ProjectList: s.ProjectList(projects=[]),
            s.SkillList: s.SkillList(
                skills=[
                    s.Skill(name="python3", category=s.SkillCategory.PROGRAMMING_LANGUAGE),
                    s.Skill(name="Odoo", category=s.SkillCategory.TECHNICAL),
                ]
            ),
            s.CertificationList: s.CertificationList(certifications=[]),
            s.SpokenLanguageList: s.SpokenLanguageList(
                spoken_languages=[
                    s.SpokenLanguage(name="Français", proficiency="Courant"),
                    s.SpokenLanguage(name="Espagnol", proficiency="Notions"),
                ]
            ),
        }
        return answers[schema]


def _analyse(cv: CV, monkeypatch: pytest.MonkeyPatch) -> None:
    """Run the background step in-process: real PDF text, fake LLM."""
    monkeypatch.setattr(django.db, "close_old_connections", lambda: None)
    content = _pdf("Yasmine Chakroun - Ariana, Tunis - Python, Odoo, Stagiaire OneTech")
    monkeypatch.setattr(
        cv_parsing, "cv_file_for_parsing", lambda cv_id: (content, "application/pdf")
    )
    pipeline.run(str(cv.pk), llm=FakeLLM())


def test_start_marks_processing_and_refuses_a_second_start(
    phase3: dict[str, Any], cv: CV, spawned: list[UUID]
) -> None:
    client = _client(phase3["candidate"])

    response = client.post(f"/api/v1/cvs/{cv.pk}/parse/")

    assert response.status_code == 202, response.content
    assert response.json()["parse_status"] == "PROCESSING"
    assert spawned == [cv.pk]
    assert client.post(f"/api/v1/cvs/{cv.pk}/parse/").status_code == 409


def test_other_people_cannot_analyse_or_read_a_cv(
    phase3: dict[str, Any], cv: CV, spawned: list[UUID]
) -> None:
    other = _client(phase3["other_candidate"])
    assert other.post(f"/api/v1/cvs/{cv.pk}/parse/").status_code == 404
    assert other.get(f"/api/v1/cvs/{cv.pk}/profile-proposal/").status_code == 404
    assert spawned == []


def test_proposal_before_analysis_is_refused(phase3: dict[str, Any], cv: CV) -> None:
    response = _client(phase3["candidate"]).get(f"/api/v1/cvs/{cv.pk}/profile-proposal/")
    assert response.status_code == 400


def test_analysis_stores_raw_result_and_proposes_resolved_entries(
    phase3: dict[str, Any], cv: CV, monkeypatch: pytest.MonkeyPatch
) -> None:
    Skill.objects.create(canonical_name="Python")
    _analyse(cv, monkeypatch)
    cv.refresh_from_db()
    assert cv.parse_status == "PARSED"
    stored = cv.parsed_data_json
    assert stored is not None
    assert stored["provider"] == "fake"
    assert stored["extraction"]["personal_information"]["full_name"]

    proposal = _client(phase3["candidate"]).get(f"/api/v1/cvs/{cv.pk}/profile-proposal/").json()

    assert proposal["identity"]["first_name"] == "Yasmine"
    assert proposal["identity"]["governorate"] == "Ariana"
    assert proposal["experiences"][0]["start_date"] == "2025-07-01"
    assert proposal["experiences"][0]["end_date"] == "2025-08-01"
    education = proposal["educations"][0]
    assert education["start_year"] == 2024 and education["end_year"] is None
    assert education["education_level"] == str(
        EducationLevel.objects.get(name="Master / Ingénieur (Bac+5)").pk
    )
    skills = {item["name"]: item["skill_id"] for item in proposal["skills"]}
    assert skills["Python"] == str(Skill.objects.get(canonical_name="Python").pk)  # "python3"
    assert skills["Odoo"] is None  # new, created only on confirmation
    languages = {item["name"]: item for item in proposal["languages"]}
    assert languages["Français"]["level"] == "C1"
    assert languages["Français"]["language_id"] == str(Language.objects.get(code="fr").pk)
    assert languages["Espagnol"]["language_id"] is None


def test_apply_writes_only_confirmed_entries_and_creates_new_skills(
    phase3: dict[str, Any], cv: CV, monkeypatch: pytest.MonkeyPatch
) -> None:
    python = Skill.objects.create(canonical_name="Python")
    profile = phase3["candidate_profile"]
    CandidateSkill.objects.create(candidate=profile, skill=python, level="EXPERT")
    _analyse(cv, monkeypatch)
    level = EducationLevel.objects.get(name="Master / Ingénieur (Bac+5)")
    body = {
        "experiences": [
            {
                "job_title": "Stagiaire",
                "organization_name": "OneTech",
                "start_date": "2025-07-01",
                "end_date": "2025-08-31",
                "description": "- Migration Odoo",
            }
        ],
        "educations": [
            {
                "education_level": str(level.pk),
                "institution": "FSB",
                "field_of_study": "Génie Logiciel",
                "start_year": 2024,
                "end_year": None,
            }
        ],
        "skills": [
            {"name": "python", "level": "INTERMEDIATE"},  # already on the profile: kept as is
            {"name": "Odoo", "category": "technical", "level": "INTERMEDIATE"},
        ],
        "languages": [{"language_id": str(Language.objects.get(code="fr").pk), "level": "C1"}],
        "projects": [{"name": "Mahara Match", "technologies": ["Django", "react.js"]}],
    }

    response = _client(phase3["candidate"]).post(
        f"/api/v1/cvs/{cv.pk}/apply-proposal/", body, format="json"
    )

    assert response.status_code == 201, response.content
    assert response.json() == {
        "experiences": 1,
        "educations": 1,
        "skills": 1,
        "languages": 1,
        "certifications": 0,
        "projects": 1,
    }
    assert Experience.objects.filter(candidate=profile, organization_name="OneTech").exists()
    assert Education.objects.get(candidate=profile).education_level == level
    odoo = CandidateSkill.objects.get(candidate=profile, skill__canonical_name="Odoo")
    assert (odoo.source, odoo.validated) == ("CV", False)
    assert CandidateSkill.objects.get(candidate=profile, skill=python).level == "EXPERT"
    assert CandidateLanguage.objects.filter(candidate=profile, level="C1").count() == 1
    project = Project.objects.get(candidate=profile)
    assert sorted(project.technologies.values_list("canonical_name", flat=True)) == [
        "Django",
        "React",
    ]

    # Reviewing again: what was just added comes back flagged, so it is not duplicated.
    again = _client(phase3["candidate"]).get(f"/api/v1/cvs/{cv.pk}/profile-proposal/").json()
    assert again["experiences"][0]["already_on_profile"] is True
    assert again["educations"][0]["already_on_profile"] is True
    assert {s["name"]: s["already_on_profile"] for s in again["skills"]}["Odoo"] is True


def test_apply_is_all_or_nothing(
    phase3: dict[str, Any], cv: CV, monkeypatch: pytest.MonkeyPatch
) -> None:
    _analyse(cv, monkeypatch)
    body = {
        "experiences": [
            {"job_title": "A", "organization_name": "B", "start_date": "2025-07-01"},
            # end before start: the model's own rule refuses it
            {
                "job_title": "C",
                "organization_name": "D",
                "start_date": "2025-07-01",
                "end_date": "2024-01-01",
            },
        ]
    }

    response = _client(phase3["candidate"]).post(
        f"/api/v1/cvs/{cv.pk}/apply-proposal/", body, format="json"
    )

    assert response.status_code == 400, response.content
    assert not Experience.objects.filter(candidate=phase3["candidate_profile"]).exists()


def test_a_failed_analysis_is_reported_on_the_cv(
    phase3: dict[str, Any], cv: CV, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        cv_parsing, "cv_file_for_parsing", lambda cv_id: (_pdf(" "), "application/pdf")
    )
    monkeypatch.setattr("django.setup", lambda: None)

    assert pipeline.main(["--cv-id", str(cv.pk)]) == 1
    cv.refresh_from_db()
    assert cv.parse_status == "FAILED"
    assert cv.parsed_data_json is not None
    assert "No readable text" in cv.parsed_data_json["error"]
