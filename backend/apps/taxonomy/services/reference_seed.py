# Placement: backend/apps/taxonomy/services/reference_seed.py
"""Demo reference vocabulary: ESCO skills and Tunisian education levels.

Rows are found by natural key first; existing rows are never modified.
"""

import json
from pathlib import Path
from typing import Any

from django.db.models import Max

from backend.apps.taxonomy.models import EducationLevel, Skill

ESCO_SKILLS_FILE = Path(__file__).resolve().parent.parent / "data" / "esco_skills.json"

# Diploma names stay in French (proper names); the English-only rule is for skills.
EDUCATION_LEVELS = (
    "Baccalauréat",
    "Licence",
    "Diplôme d'ingénieur",
    "Master",
    "Doctorat",
)


def esco_skill_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = json.loads(ESCO_SKILLS_FILE.read_text(encoding="utf-8"))["skills"]
    return rows


def seed_esco_skills() -> None:
    for row in esco_skill_rows():
        Skill.objects.get_or_create(
            canonical_name=row["label"],
            defaults={
                "category": row["skill_type"],
                "description": f"{row['description']}\nESCO: {row['uri']}",
            },
        )


def seed_education_levels() -> None:
    for name in EDUCATION_LEVELS:
        if not EducationLevel.objects.filter(name=name).exists():
            # shortcut: appends after the highest order, so the list is only in diploma order
            # when none of these names existed before; renumber by hand if that matters.
            highest = EducationLevel.objects.aggregate(top=Max("level_order"))["top"] or 0
            EducationLevel.objects.create(name=name, level_order=highest + 1)
