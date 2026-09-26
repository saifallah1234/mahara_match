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
