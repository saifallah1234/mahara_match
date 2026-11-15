# Placement: tests/unit/ai/test_cv_generation.py
"""ATS-friendly CV generation: the DOCX and PDF read back cleanly with the ticket 01 parser."""

import pytest

from ai.document_intelligence.ats.analysis import analyze_cv
from ai.document_intelligence.ats.profiles import levels, roles
from ai.document_intelligence.generation.cv_writer import generate_cv
from ai.document_intelligence.parsing.cv_reader import read_cv
from tests.fixtures.cv_review.render import render

ORIGINAL = "Built ETL pipelines in Python and Airflow ingesting 12 sources into PostgreSQL"
# 25 words with capitalised words where a line would wrap: they must not be lost on read-back.
REWRITE = (
    "Built ETL pipelines in Python and Airflow ingesting 12 sources into PostgreSQL, "
    "cutting nightly load time by [X%] for Finance, Sales, Operations and Logistics Reporting Teams"
)
DRAFT = {
    "bullets": {"experience.0.0": {"original": ORIGINAL, "decision": "accept", "text": REWRITE}},
    "confirmed_skills": ["Snowflake"],
    "declined_skills": [],
    "summary": "Data engineer building batch pipelines in Python and Airflow.",
}


@pytest.mark.parametrize("file_format", ["pdf", "docx"])
def test_generated_cv_reads_back_clean_with_standard_headings(file_format: str) -> None:
    role, level = roles()["data_engineer"], levels()["junior"]
    generated = generate_cv(render("de_image_docx"), DRAFT, role, level, file_format)

    cv = read_cv(generated.content)
    assert cv.format_risks == {}  # the image in the source is not carried over
    assert [key for key in cv.sections if key != "header"] == [
        "summary",
        "experience",
        "projects",
        "skills",
        "education",
        "other",
    ]
    assert cv.lines[0] == "Amina Example"
    assert REWRITE in cv.bullets and ORIGINAL not in cv.bullets
    assert "Migrated 40 batch jobs to Spark on AWS, cutting runtime by 35%" in cv.bullets
    assert any("Snowflake" in line for line in cv.sections["skills"])
    assert cv.sections["summary"] == [DRAFT["summary"]]
    assert "English (fluent), French (fluent), Arabic (native)" in cv.sections["other"]
    assert generated.placeholders == 1
    assert generated.missing_sections == []

    result = analyze_cv(generated.content, "data_engineer", "junior")
    codes = {issue["code"] for issue in result.issues}
    assert not codes & {"section_order", "missing_sections", "unusual_fonts", "multi_column"}


def test_software_engineer_order_and_level_missing_sections() -> None:
    role, level = roles()["software_engineer"], levels()["junior"]
    generated = generate_cv(render("de_missing_sections"), {}, role, level, "pdf")

    cv = read_cv(generated.content)
    assert [key for key in cv.sections if key != "header"] == [
        "summary",
        "experience",
        "education",
        "other",
    ]
    assert generated.placeholders == 0
    assert generated.missing_sections == ["skills", "projects"]  # junior requires both


def test_unknown_format_is_refused() -> None:
    role, level = roles()["data_engineer"], levels()["junior"]
    with pytest.raises(ValueError):
        generate_cv(render("de_good_pdf"), {}, role, level, "odt")
