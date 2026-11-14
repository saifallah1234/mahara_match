# Placement: tests/integration/test_esco_skills.py
"""ESCO loading and tier-1 skill matching (exact on normalized preferred/local names)."""

from typing import Any

import pytest
from rest_framework.test import APIClient

from backend.apps.candidates.models import CandidateSkill
from backend.apps.taxonomy.models import Skill, SkillLabel
from backend.apps.taxonomy.services import catalog
from backend.apps.taxonomy.services.esco import load_esco
from backend.apps.taxonomy.services.skills import find_skill, get_or_create_skill

pytestmark = pytest.mark.integration

URI = "http://data.europa.eu/esco/skill/"


def _row(
    uid: str, fr: str, en: str, ar: str = "", *, alt_en: str = "", digital: str = "0"
) -> dict[str, str]:
    return {
        "uri": URI + uid,
        "skill_type": "knowledge",
        "reuse_level": "sector-specific",
        "digital": digital,
        "preferred_fr": fr,
        "preferred_en": en,
        "preferred_ar": ar,
        "alternatives_fr": "",
        "alternatives_en": alt_en,
        "alternatives_ar": "",
    }


ROWS = [
    _row(
        "py",
        "Python (programmation informatique)",
        "Python (computer programming)",
        "بايثون",
        alt_en="Python3\nPy3K",
        digital="1",
    ),
    _row("ml", "apprentissage automatique", "machine learning"),
    _row(
        "scm",
        "outils de gestion de configuration logicielle",
        "tools for software configuration management",
        alt_en="Git\nSubversion",
    ),
    _row("sales-a", "vente", "sales"),
    _row("sales-b", "vente", "selling"),  # two ESCO skills share the French name
]


@pytest.fixture
def loaded(db: None) -> dict[str, Any]:
    python = Skill.objects.create(canonical_name="Python")
    git = Skill.objects.create(canonical_name="Git")
    report = load_esco(ROWS)
    return {"python": python, "git": git, "report": report}


def test_loader_links_exact_local_names_and_creates_the_rest(loaded: dict[str, Any]) -> None:
    report = loaded["report"]
    python = Skill.objects.get(pk=loaded["python"].pk)
    assert python.esco_uri == URI + "py" and python.canonical_name == "Python"  # name kept
    assert python.is_digital is True
    assert (
        Skill.objects.get(pk=loaded["git"].pk).esco_uri is None
    )  # "Git" is only an alternative label
    assert report.linked_local == [("Python", "Python (programmation informatique)")]
    assert report.created == 4
    names = set(
        Skill.objects.filter(esco_uri__startswith=URI + "sales").values_list(
            "canonical_name", flat=True
        )
    )
    assert names == {"vente", "vente (selling)"}  # unique names despite the shared label

    again = load_esco(ROWS)
    assert (again.created, again.linked_local) == (0, [])
    assert Skill.objects.count() == 6
    # The linked local name keeps a LOCAL label: still found by name and kept in lists.
    assert SkillLabel.objects.filter(skill=python, kind="LOCAL").count() == 1


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("python", "Python"),
        ("Python3", "Python"),  # alias table -> preferred label
        ("بايثون", "Python"),  # Arabic preferred label
        ("Machine Learning", "apprentissage automatique"),
        ("APPRENTISSAGE AUTOMATIQUE", "apprentissage automatique"),
        ("Git", "Git"),  # the local skill, not the broad ESCO configuration-tools skill
        ("Subversion", None),  # alternative labels never link on their own
        ("vente", None),  # ambiguous: two ESCO skills
        ("Docker", None),
    ],
)
def test_tier_one_matching(loaded: dict[str, Any], text: str, expected: str | None) -> None:
    skill = find_skill(text)
    assert (skill.canonical_name if skill else None) == expected


def test_new_local_skills_are_findable_and_esco_ones_are_reused(loaded: dict[str, Any]) -> None:
    docker = get_or_create_skill("docker")
    assert docker.canonical_name == "Docker" and docker.esco_uri is None
    assert find_skill("DOCKER") == docker
    assert get_or_create_skill("machine learning").esco_uri == URI + "ml"


def test_working_catalogue_hides_unused_esco_skills_and_search_reaches_them(
    phase3: dict[str, Any], loaded: dict[str, Any]
) -> None:
    ml = Skill.objects.get(esco_uri=URI + "ml")
    assert set(catalog.skills().values_list("canonical_name", flat=True)) == {"Python", "Git"}
    CandidateSkill.objects.create(candidate=phase3["candidate_profile"], skill=ml, level="ADVANCED")
    assert ml in catalog.skills()

    client = APIClient()
    client.force_authenticate(phase3["candidate"])
    listed = client.get("/api/v1/skills/").json()
    assert {s["canonical_name"] for s in listed["results"]} == {
        "Python",
        "Git",
        "apprentissage automatique",
    }
    found = client.get("/api/v1/skills/", {"search": "subversion"}).json()
    assert [s["esco_uri"] for s in found["results"]] == [URI + "scm"]
