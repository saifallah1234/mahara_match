from typing import Any, cast

import pytest

from backend.apps.recruitment.models import (
    Application,
    ApplicationStatus,
    JobOffer,
    JobOfferStatus,
    OfferSkill,
)

pytestmark = pytest.mark.unit


def _constraint_names(model: Any) -> set[str]:
    return {constraint.name for constraint in model._meta.constraints}


def test_job_offer_status_values_match_the_data_model() -> None:
    assert set(JobOfferStatus.values) == {"DRAFT", "PUBLISHED", "PAUSED", "CLOSED", "ARCHIVED"}


def test_application_status_values_match_the_data_model() -> None:
    assert set(ApplicationStatus.values) == {
        "SUBMITTED",
        "UNDER_REVIEW",
        "PRESELECTED",
        "INTERVIEW",
        "OFFERED",
        "HIRED",
        "REJECTED",
        "WITHDRAWN",
    }


def test_new_offers_start_as_draft() -> None:
    assert JobOffer._meta.get_field("status").default == JobOfferStatus.DRAFT


def test_easy_apply_has_no_guessed_default() -> None:
    assert not cast(Any, JobOffer._meta.get_field("easy_apply")).has_default()


def test_job_offer_constraints_are_declared() -> None:
    assert _constraint_names(JobOffer) == {
        "job_offers_source_external_id_unique",
        "job_offers_max_salary_gte_min_salary",
    }


def test_duplicate_prevention_constraints_are_declared() -> None:
    assert "applications_candidate_offer_unique" in _constraint_names(Application)
    assert "offer_skills_offer_skill_unique" in _constraint_names(OfferSkill)
