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
    Project,
    Relocation,
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
            "role_profile_id",
            "role_profile_version",
            "level",
            "breakdown_json",
            "cv_draft_json",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CVAnalysisCreateSerializer(serializers.Serializer[dict[str, Any]]):
    cv = serializers.UUIDField()
    role_profile_id = serializers.CharField(max_length=64)
    level = serializers.CharField(max_length=20)


class RoleProfileSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.CharField()
    label = serializers.CharField()  # type: ignore[assignment]  # role label, not Field.label
    version = serializers.CharField()


class CVRewriteRequestSerializer(serializers.Serializer[dict[str, Any]]):
    bullet = serializers.CharField(max_length=40, help_text='e.g. "experience.0.2"')


class CVRewriteSerializer(serializers.Serializer[dict[str, Any]]):
    original = serializers.CharField(required=False)
    text = serializers.CharField(allow_null=True)
    source = serializers.ChoiceField(choices=("model", "rule"))  # type: ignore[assignment]  # response key, not Field.source
    suggestion = serializers.CharField(allow_null=True)


class CVDraftUpdateSerializer(serializers.Serializer[dict[str, Any]]):
    """Exactly one change: a bullet decision, a missing-skill answer or the summary."""

    bullet = serializers.CharField(max_length=40, required=False)
    decision = serializers.ChoiceField(choices=("accept", "reject"), required=False)
    text = serializers.CharField(max_length=300, required=False, allow_blank=True)
    skill = serializers.CharField(max_length=100, required=False)
    has_experience = serializers.BooleanField(required=False)
    summary = serializers.CharField(max_length=600, required=False, allow_blank=True)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        groups = [
            "bullet" in attrs and "decision" in attrs,
            "skill" in attrs and "has_experience" in attrs,
            "summary" in attrs,
        ]
        if sum(groups) != 1:
            raise serializers.ValidationError(
                "Send exactly one of: bullet and decision, skill and has_experience, or summary."
            )
        for name in ("text", "summary"):
            if "\n" in attrs.get(name, "").strip():
                raise serializers.ValidationError({name: "Must be a single line."})
        return attrs
