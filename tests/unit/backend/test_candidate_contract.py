from typing import Any, cast

import pytest
from django.urls import resolve

from backend.apps.candidates.api.serializers import CandidateProfileSerializer, CVSerializer
from backend.apps.candidates.models import (
    CV,
    CandidateLanguage,
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    CVAnalysisResult,
    Education,
    Experience,
    Project,
    ProjectSkill,
)

pytestmark = pytest.mark.unit


def _actions(path: str) -> dict[str, str]:
    return cast(Any, resolve(path).func).actions


def test_candidate_routes_have_no_delete() -> None:
    assert "delete" not in _actions("/api/v1/cvs/00000000-0000-0000-0000-000000000001/")
    assert _actions("/api/v1/cv-analysis-results/") == {"get": "list"}
    assert _actions("/api/v1/documents/") == {"get": "list"}


def test_candidate_sensitive_fields_are_read_only() -> None:
    profile = CandidateProfileSerializer()
    cv = CVSerializer()
    assert profile.fields["completion_score"].read_only
    assert cv.fields["parsed_data_json"].read_only
    assert cv.fields["version_number"].read_only


def test_candidate_table_and_relationship_contract() -> None:
    assert CandidateProfile._meta.db_table == "candidate_profiles"
    assert CandidateProfile._meta.get_field("user").unique
    assert CandidatePreference._meta.get_field("candidate").unique
    assert CV._meta.get_field("document").unique
    assert (
        CVAnalysisResult._meta.get_field("target_offer").remote_field.model
        == "recruitment.JobOffer"
    )
    assert Project._meta.get_field("technologies").remote_field.through is ProjectSkill
    for model in (Experience, Education, CandidateLanguage, CandidateSkill):
        assert model._meta.get_field("candidate") is not None


def test_required_candidate_constraints_exist() -> None:
    assert {item.name for item in CV._meta.constraints} >= {
        "cvs_candidate_version_unique",
        "cvs_one_primary_per_candidate",
    }
    assert {item.name for item in CandidateSkill._meta.constraints} >= {
        "candidate_skills_unique",
        "candidate_skills_years_nonnegative",
    }
