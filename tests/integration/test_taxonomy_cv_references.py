# Placement: tests/integration/test_taxonomy_cv_references.py
"""Education level seed and skill normalization used by CV extraction."""

import pytest
from django.core.management import call_command

from backend.apps.taxonomy.models import EducationLevel, Skill
from backend.apps.taxonomy.services.education import EDUCATION_LEVELS, level_for_degree
from backend.apps.taxonomy.services.skills import (
    canonical_skill_name,
    find_skill,
    get_or_create_skill,
)

pytestmark = pytest.mark.integration


def test_education_levels_seed_once_and_keep_admin_rows(db: None) -> None:
    EducationLevel.objects.create(name="Licence (Bac+3)", level_order=7, description="admin")

    call_command("seed_education_levels", verbosity=0)
    call_command("seed_education_levels", verbosity=0)

    assert EducationLevel.objects.count() == len(EDUCATION_LEVELS)
    assert EducationLevel.objects.get(name="Licence (Bac+3)").description == "admin"
    assert level_for_degree("master").name == "Master / Ingénieur (Bac+5)"  # type: ignore[union-attr]
    assert level_for_degree("short_cycle") == level_for_degree("associate")
    assert level_for_degree(None) is None


@pytest.mark.parametrize(
    ("raw", "canonical"),
    [("js", "JavaScript"), ("Python3", "Python"), ("  react.js ", "React"), ("Odoo", "Odoo")],
)
def test_canonical_names(raw: str, canonical: str) -> None:
    assert canonical_skill_name(raw) == canonical


def test_skills_are_found_case_and_accent_insensitively_and_created_once(db: None) -> None:
    existing = Skill.objects.create(canonical_name="Développement Web")

    assert find_skill("developpement web") == existing
    created = get_or_create_skill("postgres", "technical")
    assert created.canonical_name == "PostgreSQL"
    assert get_or_create_skill("PostgreSQL") == created
    assert Skill.objects.filter(canonical_name__iexact="postgresql").count() == 1
