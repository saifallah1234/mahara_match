# Placement: tests/integration/identity/test_seed_demo.py
from io import StringIO

import pytest
from django.apps import apps
from django.conf import settings as django_settings
from django.core.management import CommandError, call_command
from django.urls import reverse
from rest_framework.test import APIClient

from backend.apps.identity.models import User, UserRole

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
