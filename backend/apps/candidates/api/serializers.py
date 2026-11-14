from typing import Any

from rest_framework import serializers

from backend.apps.candidates.models import (
    CV,
    CandidateLanguage,
    CandidatePreference,
    CandidateProfile,
    CandidateSkill,
    Certification,
    CVAnalysisResult,
    Education,
    Experience,
    LanguageLevel,
    Project,
    Relocation,
    SkillLevel,
    WorkMode,
)
from backend.apps.documents.models import Document
from backend.apps.taxonomy.models import Skill


class CandidateProfileSerializer(serializers.ModelSerializer[CandidateProfile]):
    class Meta:
        model = CandidateProfile
        fields = (
            "id",
            "birth_date",
            "country_code",
            "governorate",
            "city",
            "headline",
            "summary",
            "employment_status",
            "desired_job_title",
            "availability_date",
            "profile_visibility",
            "completion_score",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "completion_score", "created_at", "updated_at")


class RecruiterSkillSerializer(serializers.ModelSerializer[CandidateSkill]):
    class Meta:
        model = CandidateSkill
        fields = ("skill", "level", "years_experience")
        read_only_fields = fields


class RecruiterExperienceSerializer(serializers.ModelSerializer[Experience]):
    class Meta:
        model = Experience
        fields = ("organization_name", "job_title", "start_date", "end_date")
        read_only_fields = fields


class RecruiterEducationSerializer(serializers.ModelSerializer[Education]):
    class Meta:
        model = Education
        fields = ("education_level", "institution", "field_of_study", "start_year", "end_year")
        read_only_fields = fields


class RecruiterPreferenceSerializer(serializers.ModelSerializer[CandidatePreference]):
    class Meta:
        model = CandidatePreference
        fields = ("work_mode", "relocation", "distance")
        read_only_fields = fields


class RecruiterCandidateSerializer(serializers.ModelSerializer[CandidateProfile]):
    skills = RecruiterSkillSerializer(many=True, read_only=True)
    experiences = RecruiterExperienceSerializer(many=True, read_only=True)
    educations = RecruiterEducationSerializer(many=True, read_only=True)
    preferences = RecruiterPreferenceSerializer(read_only=True, allow_null=True)

    class Meta:
        model = CandidateProfile
        fields = (
            "id",
            "headline",
            "skills",
            "experiences",
            "educations",
            "governorate",
            "preferences",
        )
        read_only_fields = fields


class CandidateDiscoveryQuerySerializer(serializers.Serializer[dict[str, object]]):
    skill = serializers.UUIDField(required=False)
    education_level = serializers.UUIDField(required=False)
    governorate = serializers.CharField(max_length=100, required=False)
    work_mode = serializers.ChoiceField(choices=WorkMode.choices, required=False)
    relocation = serializers.ChoiceField(choices=Relocation.choices, required=False)
    search = serializers.CharField(max_length=200, required=False)


class ExperienceSerializer(serializers.ModelSerializer[Experience]):
    class Meta:
        model = Experience
        fields = (
            "id",
            "organization_name",
            "job_title",
            "start_date",
            "end_date",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class EducationSerializer(serializers.ModelSerializer[Education]):
    class Meta:
        model = Education
        fields = (
            "id",
            "education_level",
            "institution",
            "field_of_study",
            "start_year",
            "end_year",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CandidateLanguageSerializer(serializers.ModelSerializer[CandidateLanguage]):
    class Meta:
        model = CandidateLanguage
        fields = ("id", "language", "level", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class CandidateSkillSerializer(serializers.ModelSerializer[CandidateSkill]):
    class Meta:
        model = CandidateSkill
        fields = (
            "id",
            "skill",
            "level",
            "years_experience",
            "validated",
            "source",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "validated", "source", "created_at", "updated_at")


class CertificationSerializer(serializers.ModelSerializer[Certification]):
    class Meta:
        model = Certification
        fields = (
            "id",
            "name",
            "description",
            "certification_organization",
            "issue_date",
            "expiration_date",
            "credential_id",
            "credential_url",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CandidatePreferenceSerializer(serializers.ModelSerializer[CandidatePreference]):
    class Meta:
        model = CandidatePreference
        fields = ("id", "work_mode", "relocation", "distance", "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class ProjectSerializer(serializers.ModelSerializer[Project]):
    technologies = serializers.PrimaryKeyRelatedField(
        queryset=Skill.objects.all(), many=True, required=False
    )

    class Meta:
        model = Project
        fields = (
            "id",
            "name",
            "description",
            "role",
            "start_date",
            "end_date",
            "project_url",
            "repository_url",
            "technologies",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class CVSerializer(serializers.ModelSerializer[CV]):
    document = serializers.PrimaryKeyRelatedField(queryset=Document.objects.all())

    class Meta:
        model = CV
        fields = (
            "id",
            "document",
            "title",
            "language_code",
            "is_primary",
            "parse_status",
            "parsed_data_json",
            "version_number",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "parse_status",
            "parsed_data_json",
            "version_number",
            "created_at",
            "updated_at",
        )


class CVAnalysisResultSerializer(serializers.ModelSerializer[CVAnalysisResult]):
    class Meta:
        model = CVAnalysisResult
        fields = (
            "id",
            "cv",
            "target_offer",
            "overall_score",
            "issues_json",
            "suggestions_json",
            "analyzed_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


# -- CV analysis: what the candidate confirms from the proposal ---------------------


class _ProposedExperienceSerializer(serializers.Serializer[dict[str, Any]]):
    job_title = serializers.CharField(max_length=150)
    organization_name = serializers.CharField(max_length=200)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, default="")


class _ProposedEducationSerializer(serializers.Serializer[dict[str, Any]]):
    education_level = serializers.UUIDField()
    institution = serializers.CharField(max_length=200)
    field_of_study = serializers.CharField(
        max_length=150, required=False, allow_blank=True, default=""
    )
    start_year = serializers.IntegerField(min_value=1900, max_value=2100)
    end_year = serializers.IntegerField(
        min_value=1900, max_value=2100, required=False, allow_null=True
    )
    description = serializers.CharField(required=False, allow_blank=True, default="")


class _ProposedSkillSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=150)
    category = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    level = serializers.ChoiceField(choices=SkillLevel.choices)


class _ProposedLanguageSerializer(serializers.Serializer[dict[str, Any]]):
    language_id = serializers.UUIDField()
    level = serializers.ChoiceField(choices=LanguageLevel.choices)


class _ProposedCertificationSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=200)
    certification_organization = serializers.CharField(max_length=200)
    issue_date = serializers.DateField()
    description = serializers.CharField(required=False, allow_blank=True, default="")


class _ProposedProjectSerializer(serializers.Serializer[dict[str, Any]]):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    repository_url = serializers.URLField(
        max_length=500, required=False, allow_blank=True, default=""
    )
    technologies = serializers.ListField(
        child=serializers.CharField(max_length=150), required=False, default=list, max_length=50
    )


class CVProposalApplySerializer(serializers.Serializer[dict[str, Any]]):
    experiences = _ProposedExperienceSerializer(many=True, required=False, default=list)
    educations = _ProposedEducationSerializer(many=True, required=False, default=list)
    skills = _ProposedSkillSerializer(many=True, required=False, default=list)
    languages = _ProposedLanguageSerializer(many=True, required=False, default=list)
    certifications = _ProposedCertificationSerializer(many=True, required=False, default=list)
    projects = _ProposedProjectSerializer(many=True, required=False, default=list)
