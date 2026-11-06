from datetime import date

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.candidates.models import Experience, Project, ProjectSkill
from backend.apps.taxonomy.models import Skill

pytestmark = pytest.mark.django_db


def client_for(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_candidate_deletes_own_experience(phase3):
    experience = Experience.objects.create(
        candidate=phase3["candidate_profile"],
        job_title="Développeur",
        organization_name="Acme",
        start_date=date(2020, 1, 1),
    )
    url = reverse("experience-detail", args=(experience.id,))

    assert client_for(phase3["candidate"]).delete(url).status_code == 204
    assert not Experience.objects.filter(pk=experience.pk).exists()


def test_candidate_cannot_delete_another_candidates_experience(phase3):
    experience = Experience.objects.create(
        candidate=phase3["candidate_profile"],
        job_title="Développeur",
        organization_name="Acme",
        start_date=date(2020, 1, 1),
    )
    url = reverse("experience-detail", args=(experience.id,))

    assert client_for(phase3["other_candidate"]).delete(url).status_code == 404
    assert Experience.objects.filter(pk=experience.pk).exists()


def test_candidate_deletes_project_with_technologies(phase3):
    skill = Skill.objects.create(canonical_name="Python")
    project = Project.objects.create(candidate=phase3["candidate_profile"], name="Portail")
    ProjectSkill.objects.create(project=project, skill=skill)
    url = reverse("project-detail", args=(project.id,))

    assert client_for(phase3["candidate"]).delete(url).status_code == 204
    assert not Project.objects.filter(pk=project.pk).exists()
    assert not ProjectSkill.objects.filter(skill=skill).exists()
