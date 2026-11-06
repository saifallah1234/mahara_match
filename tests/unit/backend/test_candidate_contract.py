from typing import Any, cast

import pytest
from django.urls import resolve
from drf_spectacular.generators import SchemaGenerator

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
from backend.apps.recruitment.models import JobOffer

pytestmark = pytest.mark.unit


def _actions(path: str) -> dict[str, str]:
    return {
        method: action
        for method, action in cast(Any, resolve(path).func).actions.items()
        if method != "head"
    }


def test_candidate_routes_expose_only_approved_delete() -> None:
    assert _actions("/api/v1/cvs/00000000-0000-0000-0000-000000000001/")["delete"] == ("destroy")
    assert _actions("/api/v1/cv-analysis-results/") == {"get": "list", "post": "create"}
    assert _actions("/api/v1/documents/") == {"get": "list", "post": "create"}


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
    assert CVAnalysisResult._meta.get_field("target_offer").remote_field.model is JobOffer
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


def test_discovery_routes_and_openapi_use_redacted_contract() -> None:
    assert _actions("/api/v1/candidate-profiles/") == {"get": "list"}
    assert _actions("/api/v1/candidate-profiles/00000000-0000-0000-0000-000000000001/") == {
        "get": "retrieve"
    }
    assert _actions("/api/v1/candidate-profiles/me/") == {
        "get": "me",
        "post": "me",
        "put": "me",
        "patch": "me",
    }
    schema = SchemaGenerator().get_schema(public=True)
    paths = cast(dict[str, Any], schema["paths"])
    schemas = schema["components"]["schemas"]
    listing = paths["/api/v1/candidate-profiles/"]["get"]
    response = listing["responses"]["200"]["content"]["application/json"]["schema"]
    assert response["$ref"] == "#/components/schemas/PaginatedRecruiterCandidateList"
    detail = paths["/api/v1/candidate-profiles/{id}/"]["get"]
    assert detail["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/RecruiterCandidate"
    )
    assert set(schemas["RecruiterCandidate"]["properties"]) == {
        "id",
        "headline",
        "skills",
        "experiences",
        "educations",
        "governorate",
        "preferences",
    }
    assert {parameter["name"] for parameter in listing["parameters"]} == {
        "page",
        "page_size",
        "skill",
        "education_level",
        "governorate",
        "work_mode",
        "relocation",
        "search",
    }
    self_read = paths["/api/v1/candidate-profiles/me/"]["get"]
    assert self_read["responses"]["200"]["content"]["application/json"]["schema"]["$ref"] == (
        "#/components/schemas/CandidateProfile"
    )
