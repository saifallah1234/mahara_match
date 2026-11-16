# Placement: backend/apps/taxonomy/services/education.py
"""The education level scale (decision 2026-11-14) and degree-level lookups.

Levels follow the Tunisian Bac+N scale, with the EQF level as a reference.
CV extraction classifies each diploma into a DEGREE_LEVEL key; DEGREE_LEVEL_TO_NAME
maps that key to a row of this scale.
"""

from backend.apps.taxonomy.models import EducationLevel

# (name, level_order, description). Order is the comparison order (higher = more study).
EDUCATION_LEVELS: tuple[tuple[str, int, str], ...] = (
    ("Sans diplôme", 10, "No diploma completed."),
    ("Baccalauréat", 20, "Secondary school leaving diploma (EQF 4)."),
    ("Bac+2 (BTS, DUT, cycle préparatoire)", 30, "Two years of higher education (EQF 5)."),
    ("Licence (Bac+3)", 40, "Bachelor level (EQF 6)."),
    ("Master / Ingénieur (Bac+5)", 50, "Master level, including Diplôme d'Ingénieur (EQF 7)."),
    ("Doctorat (Bac+8)", 60, "Doctorate (EQF 8)."),
    ("Autre", 90, "Other or unclassified qualification."),
)

DEGREE_LEVEL_TO_NAME: dict[str, str] = {
    "none": "Sans diplôme",
    "high_school": "Baccalauréat",
    "short_cycle": "Bac+2 (BTS, DUT, cycle préparatoire)",
    "associate": "Bac+2 (BTS, DUT, cycle préparatoire)",
    "bachelor": "Licence (Bac+3)",
    "master": "Master / Ingénieur (Bac+5)",
    "doctorate": "Doctorat (Bac+8)",
    "other": "Autre",
}


def seed_education_levels() -> int:
    """Create the missing levels; existing rows are never changed. Returns the count created."""
    created = 0
    for name, order, description in EDUCATION_LEVELS:
        if EducationLevel.objects.filter(name=name).exists():
            continue
        if EducationLevel.objects.filter(level_order=order).exists():
            continue  # an admin already used this slot for another level
        EducationLevel.objects.create(name=name, level_order=order, description=description)
        created += 1
    return created


def level_for_degree(degree_level: str | None) -> EducationLevel | None:
    name = DEGREE_LEVEL_TO_NAME.get((degree_level or "").strip().lower())
    return EducationLevel.objects.filter(name=name).first() if name else None
