# Placement: tests/unit/ai/test_ats_analysis.py
"""Deterministic ATS analysis over the synthetic CV set (no database, no model)."""

from pathlib import Path

import pytest

from ai.document_intelligence.ats.analysis import AtsResult, CVReviewError, analyze_cv
from ai.document_intelligence.ats.profiles import RoleProfileError, load_levels, load_roles, roles
from tests.fixtures.cv_review.render import cv_spec, render, synthetic_cvs

pytestmark = pytest.mark.unit


def analyse(cv_id: str, role: str | None = None, level: str | None = None) -> AtsResult:
    spec = cv_spec(cv_id)
    return analyze_cv(render(cv_id), role or spec["role"], level or spec["level"])


def codes(result: AtsResult) -> set[str]:
    return {issue["code"] for issue in result.issues}


def skill_evidence(result: AtsResult, name: str) -> float:
    return next(row["evidence"] for row in result.breakdown["skills"] if row["name"] == name)


@pytest.mark.parametrize("spec", synthetic_cvs(), ids=lambda spec: spec["id"])
def test_synthetic_cv_reports_its_known_issues(spec):
    if spec.get("reject"):
        with pytest.raises(CVReviewError, match="English"):
            analyse(spec["id"])
        return
    result = analyse(spec["id"])
    assert set(spec.get("expect", [])) <= codes(result)
    assert not set(spec.get("absent", [])) & codes(result)
    assert 0 <= result.overall_score <= 100
    assert 0 <= result.breakdown["ats_readiness"] <= 100
    assert 0 <= result.breakdown["role_fit"] <= 100
    assert all(issue["message"] for issue in result.issues)


@pytest.mark.parametrize("fmt", ["pdf", "docx"])
def test_role_fit_discriminates_between_roles(fmt):
    data_cv, software_cv = f"de_good_{fmt}", f"se_good_{fmt}"
    assert (
        analyse(data_cv, "data_engineer").breakdown["role_fit"]
        > analyse(data_cv, "software_engineer").breakdown["role_fit"]
    )
    assert (
        analyse(software_cv, "software_engineer").breakdown["role_fit"]
        > analyse(software_cv, "data_engineer").breakdown["role_fit"]
    )


def test_scan_without_text_layer_scores_zero_parseability():
    result = analyse("de_scan_pdf")
    assert result.breakdown["components"]["parseability"] == 0
    assert result.overall_score == 0
    assert codes(result) == {"no_text_layer"}


def test_skill_used_in_a_bullet_earns_more_than_listed_only():
    good, stuffed = analyse("de_good_pdf"), analyse("de_keyword_stuffed")
    assert skill_evidence(good, "Airflow") == 1.0
    assert skill_evidence(stuffed, "Airflow") == 0.5
    assert skill_evidence(stuffed, "Data modeling") == 0.0
    assert (
        stuffed.breakdown["components"]["skill_coverage"]
        < good.breakdown["components"]["skill_coverage"]
    )


def test_weak_bullets_lower_evidence_and_content_quality():
    good, weak = analyse("de_good_pdf", level="mid"), analyse("de_weak_bullets")
    for component in ("evidence", "content"):
        assert weak.breakdown["components"][component] < good.breakdown["components"][component]
    assert weak.breakdown["bullets"]["with_weak_phrase"] == 3
    weak_issue = next(issue for issue in weak.issues if issue["code"] == "weak_phrases")
    assert weak_issue["params"]["phrases"] == {
        "responsible for": 1,
        "worked on": 1,
        "helped with": 1,
    }


def test_missing_metric_issue_names_the_role_metric_hints():
    issue = next(
        i for i in analyse("de_weak_bullets").issues if i["code"] == "bullets_without_metric"
    )
    assert "data volume (GB/TB/rows)" in issue["message"]


def test_junior_one_page_rule_is_strict_but_mid_allows_two_pages():
    junior, mid = analyse("de_long_junior"), analyse("de_long_mid")
    assert junior.breakdown["page_count"] == mid.breakdown["page_count"] == 2
    assert junior.breakdown["components"]["length"] == 0
    assert mid.breakdown["components"]["length"] == 100
    assert junior.level.weights != mid.level.weights


def test_missing_contact_details_become_issues():
    result = analyse("de_no_contact")
    assert {"missing_email", "missing_phone"} <= codes(result)
    assert result.breakdown["contacts"] == {"email": False, "phone": False, "links": 0}


def test_unknown_role_level_or_file_type_is_refused():
    pdf = render("de_good_pdf")
    with pytest.raises(CVReviewError, match="role"):
        analyze_cv(pdf, "astronaut", "junior")
    with pytest.raises(CVReviewError, match="level"):
        analyze_cv(pdf, "data_engineer", "senior")
    with pytest.raises(CVReviewError, match="PDF and DOCX"):
        analyze_cv(b"\x89PNG\r\n\x1a\nnot a cv", "data_engineer", "junior")
    with pytest.raises(CVReviewError):
        analyze_cv(b"%PDF-1.7 broken", "data_engineer", "junior")


def test_shipped_role_profiles_load_with_versions():
    assert {role.id: role.label for role in roles().values()} == {
        "data_engineer": "Data Engineer",
        "software_engineer": "Software Engineer",
    }
    assert all(role.version for role in roles().values())
    assert set(load_levels()) == {"intern", "junior", "mid"}


@pytest.mark.parametrize(
    "content",
    [
        "id: broken\nlabel: Broken\nversion: 1\n",  # no skills
        "id: other\nlabel: x\n",  # id differs from file name
        "id: broken\nlabel: [unclosed\n",  # invalid YAML
    ],
)
def test_malformed_role_profile_fails_loudly(tmp_path: Path, content: str):
    (tmp_path / "broken.yaml").write_text(content, encoding="utf-8")
    with pytest.raises(RoleProfileError):
        load_roles(tmp_path)


def test_malformed_level_table_fails_loudly(tmp_path: Path):
    path = tmp_path / "levels.yaml"
    path.write_text("levels:\n  junior:\n    label: Junior\n    weights: {parseability: 1}\n")
    with pytest.raises(RoleProfileError):
        load_levels(path)
