# Placement: tests/unit/backend/taxonomy/test_esco_skills_file.py
import re

from backend.apps.taxonomy.services.reference_seed import esco_skill_rows

ESCO_SKILL_URI = re.compile(
    r"^http://data\.europa\.eu/esco/skill/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)


def test_every_esco_row_has_a_concept_uri_and_a_unique_short_label() -> None:
    rows = esco_skill_rows()
    assert len(rows) >= 20
    labels = [row["label"] for row in rows]
    assert all(ESCO_SKILL_URI.match(row["uri"]) for row in rows)
    assert all(label.strip() and len(label) <= 150 for label in labels)
    assert len({label.casefold() for label in labels}) == len(labels)
    assert len({row["uri"] for row in rows}) == len(rows)
