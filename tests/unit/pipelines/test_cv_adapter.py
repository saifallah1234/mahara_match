# Placement: tests/unit/pipelines/test_cv_adapter.py
"""Raw CV extraction -> profile proposal (pure normalization)."""

import pytest

from pipelines.document_processing.cv_adapter import (
    build_proposal,
    cefr_level,
    clean_text,
    parse_cv_date,
    split_full_name,
)


@pytest.mark.parametrize(
    ("text", "end", "expected"),
    [
        ("Sept. 2024", False, "2024-09-01"),
        ("Juillet 2025", False, "2025-07-01"),
        ("août 2025", False, "2025-08-01"),
        ("03/2023", False, "2023-03-01"),
        ("2021", False, "2021-01-01"),
        ("2021", True, "2021-12-31"),
        ("Present", False, None),
        ("Aujourd'hui", False, None),
        ("En cours", True, None),
        ("", False, None),
        (None, False, None),
        ("bientôt", False, None),
    ],
)
def test_cv_dates(text: str | None, end: bool, expected: str | None) -> None:
    assert parse_cv_date(text, end=end) == expected


@pytest.mark.parametrize(
    ("full_name", "expected"),
    [
        ("Yasmine Chakroun", ("Yasmine", "Chakroun")),
        ("CHAKROUN Yasmine", ("Yasmine", "CHAKROUN")),
        ("Mohamed Ali Ben Salah", ("Mohamed", "Ali Ben Salah")),
        ("", ("", "")),
        (None, ("", "")),
    ],
)
def test_names(full_name: str | None, expected: tuple[str, str]) -> None:
    assert split_full_name(full_name) == expected


@pytest.mark.parametrize(
    ("proficiency", "level"),
    [
        ("B2", "B2"),
        ("Courant (C1)", "C1"),
        ("Langue maternelle", "C2"),
        ("Fluent", "C1"),
        ("Intermédiaire", "B1"),
        ("Notions", "A2"),
        ("", None),
        ("Lu, écrit", None),
    ],
)
def test_language_levels(proficiency: str, level: str | None) -> None:
    assert cefr_level(proficiency) == level


def test_proposal_shapes_every_section() -> None:
    proposal = build_proposal(
        {
            "personal_information": {
                "full_name": "Yasmine Chakroun",
                "email": "y@example.test",
                "phone": "+216 24 305 500",
                "location": "Ariana, Tunisie",
                "linkedin": None,
                "github": None,
            },
            "headline": "Étudiante en Génie Logiciel",
            "professional_summary": None,
            "experience": [
                {
                    "job_title": "Stagiaire",
                    "company": "OneTech",
                    "start_date": "Juillet 2025",
                    "end_date": "Present",
                    "is_current": True,
                    "description": None,
                    "responsibilities": ["Migration Odoo"],
                    "technologies": ["Odoo"],
                }
            ],
            "education": [
                {
                    "degree": "Licence",
                    "degree_level": "bachelor",
                    "institution": "ISI",
                    "field_of_study": None,
                    "start_date": "2019",
                    "end_date": "2022",
                    "is_current": False,
                    "description": "Mention Bien",
                }
            ],
            "skills": [{"name": " Python ", "category": "programming_language"}, {"name": " "}],
            "spoken_languages": [{"name": "Anglais", "proficiency": "B2"}],
            "certifications": [{"name": "AWS CCP", "issuer": "Amazon", "date": "Mars 2024"}],
            "projects": [
                {
                    "title": "Mahara",
                    "summary": "Plateforme",
                    "highlights": ["RAG"],
                    "technologies": ["Django "],
                    "github": "github.com/x/y",
                }
            ],
        }
    )

    identity = proposal["identity"]
    assert (identity["first_name"], identity["last_name"]) == ("Yasmine", "Chakroun")
    assert (identity["governorate"], identity["city"], identity["country_code"]) == (
        "Ariana",
        "Ariana",
        "TN",
    )
    experience = proposal["experiences"][0]
    assert (experience["start_date"], experience["end_date"]) == ("2025-07-01", None)
    assert "- Migration Odoo" in experience["description"]
    assert "Technologies : Odoo" in experience["description"]
    education = proposal["educations"][0]
    assert (education["start_year"], education["end_year"]) == (2019, 2022)
    assert education["description"] == "Licence - Mention Bien"
    assert proposal["skills"] == [{"name": "Python", "category": "programming_language"}]
    assert proposal["languages"] == [
        {"name": "Anglais", "code": "en", "proficiency": "B2", "level": "B2"}
    ]
    assert proposal["certifications"][0]["issue_date"] == "2024-03-01"
    assert proposal["projects"][0] == {
        "name": "Mahara",
        "description": "Plateforme\n- RAG",
        "repository_url": "",  # not a full URL: left for the candidate
        "technologies": ["Django"],
    }


def test_markdown_is_removed_from_identity_text() -> None:
    raw = "Étudiante en Génie Logiciel _|_ À la recherche d’un **stage** `d’été`"
    assert clean_text(raw) == "Étudiante en Génie Logiciel · À la recherche d’un stage d’été"
    assert clean_text("snake_case_name") == "snake_case_name"
    assert clean_text(None) == ""
