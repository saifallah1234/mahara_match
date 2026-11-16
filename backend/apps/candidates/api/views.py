from io import BytesIO
from typing import Any

from django.http import FileResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from backend.apps.candidates.api.serializers import (
    CandidateDiscoveryQuerySerializer,
    CandidateLanguageSerializer,
    CandidatePreferenceSerializer,
    CandidateProfileSerializer,
    CandidateSkillSerializer,
    CertificationSerializer,
    CVAnalysisCreateSerializer,
    CVAnalysisResultSerializer,
    CVDraftUpdateSerializer,
    CVGenerateSerializer,
    CVProposalApplySerializer,
    CVRewriteRequestSerializer,
    CVRewriteSerializer,
    CVSerializer,
    EducationSerializer,
    ExperienceSerializer,
    ProjectSerializer,
    RecruiterCandidateSerializer,
    RoleProfileSerializer,
)
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
from backend.apps.candidates.services import cv_parsing, cv_review, discovery, records
from backend.apps.identity.api.common_permissions import active_request_user


class CandidateProfileViewSet(GenericViewSet[CandidateProfile]):
    serializer_class = CandidateProfileSerializer
    queryset = CandidateProfile.objects.none()

    @extend_schema(
        parameters=[CandidateDiscoveryQuerySerializer],
        responses=RecruiterCandidateSerializer(many=True),
        description="Redacted discovery for authorized recruiters. RECRUITERS and PUBLIC profiles.",
    )
    def list(self, request: Request) -> Response:
        queryset = discovery.list_candidates(active_request_user(request))
        filters = CandidateDiscoveryQuerySerializer(data=request.query_params)
        filters.is_valid(raise_exception=True)
        queryset = discovery.filter_candidates(queryset, filters.validated_data)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(RecruiterCandidateSerializer(page, many=True).data)

    @extend_schema(
        responses=RecruiterCandidateSerializer,
        description="Redacted recruiter detail. PRIVATE and inactive candidates return 404.",
    )
    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        profile = discovery.get_candidate(active_request_user(request), str(pk))
        return Response(RecruiterCandidateSerializer(profile).data)

    @action(detail=False, methods=("get", "post", "put", "patch"), url_path="me")
    def me(self, request: Request) -> Response:
        actor = active_request_user(request)
        if request.method == "GET":
            return Response(CandidateProfileSerializer(records.own_profile(actor)).data)
        serializer = CandidateProfileSerializer(
            data=request.data, partial=request.method == "PATCH"
        )
        serializer.is_valid(raise_exception=True)
        if request.method == "POST":
            profile = records.create_profile(actor, serializer.validated_data)
            return Response(
                CandidateProfileSerializer(profile).data, status=status.HTTP_201_CREATED
            )
        profile = records.update_profile(actor, serializer.validated_data)
        return Response(CandidateProfileSerializer(profile).data)


class OwnedRecordViewSet(GenericViewSet[Any]):
    model: type[Any]
    queryset = CandidateProfile.objects.none()

    def list(self, request: Request) -> Response:
        queryset = records.list_records(active_request_user(request), self.model)
        page = self.paginate_queryset(queryset)
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        record = records.get_record(active_request_user(request), self.model, str(pk))
        return Response(self.get_serializer(record).data)

    def create(self, request: Request) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        actor = active_request_user(request)
        if self.model is CV:
            record = records.create_cv(actor, serializer.validated_data)
        else:
            record = records.create_record(actor, self.model, serializer.validated_data)
        return Response(self.get_serializer(record).data, status=status.HTTP_201_CREATED)

    def update(self, request: Request, pk: str | None = None) -> Response:
        return self._update(request, str(pk), partial=False)

    def partial_update(self, request: Request, pk: str | None = None) -> Response:
        return self._update(request, str(pk), partial=True)

    def _update(self, request: Request, pk: str, *, partial: bool) -> Response:
        actor = active_request_user(request)
        record = records.get_record(actor, self.model, pk)
        serializer = self.get_serializer(record, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        if self.model is CV:
            updated = records.update_cv(actor, pk, serializer.validated_data)
        else:
            updated = records.update_record(actor, self.model, pk, serializer.validated_data)
        return Response(self.get_serializer(updated).data)

    def destroy(self, request: Request, pk: str | None = None) -> Response:
        records.delete_record(active_request_user(request), self.model, str(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)


class ExperienceViewSet(OwnedRecordViewSet):
    model = Experience
    serializer_class = ExperienceSerializer


class EducationViewSet(OwnedRecordViewSet):
    model = Education
    serializer_class = EducationSerializer


class CandidateLanguageViewSet(OwnedRecordViewSet):
    model = CandidateLanguage
    serializer_class = CandidateLanguageSerializer


class CandidateSkillViewSet(OwnedRecordViewSet):
    model = CandidateSkill
    serializer_class = CandidateSkillSerializer


class CertificationViewSet(OwnedRecordViewSet):
    model = Certification
    serializer_class = CertificationSerializer


class CandidatePreferenceViewSet(OwnedRecordViewSet):
    model = CandidatePreference
    serializer_class = CandidatePreferenceSerializer


class ProjectViewSet(OwnedRecordViewSet):
    model = Project
    serializer_class = ProjectSerializer


class CVViewSet(OwnedRecordViewSet):
    model = CV
    serializer_class = CVSerializer

    def destroy(self, request: Request, pk: str | None = None) -> Response:
        records.delete_cv(active_request_user(request), str(pk))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(request=None, responses={202: CVSerializer})
    @action(detail=True, methods=["post"])
    def parse(self, request: Request, pk: str | None = None) -> Response:
        """Start the analysis of this CV in the background; poll parse_status."""
        cv = cv_parsing.request_cv_parsing(active_request_user(request), str(pk))
        return Response(CVSerializer(cv).data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(request=None, responses=dict[str, Any])
    @action(detail=True, methods=["get"], url_path="profile-proposal")
    def profile_proposal(self, request: Request, pk: str | None = None) -> Response:
        """What the analysis found, shaped like profile records, for the candidate to review."""
        return Response(cv_parsing.cv_profile_proposal(active_request_user(request), str(pk)))

    @extend_schema(request=CVProposalApplySerializer, responses=dict[str, int])
    @action(detail=True, methods=["post"], url_path="apply-proposal")
    def apply_proposal(self, request: Request, pk: str | None = None) -> Response:
        """Add the entries the candidate confirmed to their profile (all or nothing)."""
        serializer = CVProposalApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        counts = cv_parsing.apply_cv_proposal(
            active_request_user(request), str(pk), serializer.validated_data
        )
        return Response(counts, status=status.HTTP_201_CREATED)


class CVAnalysisResultViewSet(GenericViewSet[CVAnalysisResult]):
    queryset = CVAnalysisResult.objects.none()
    serializer_class = CVAnalysisResultSerializer

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(records.list_cv_analyses(active_request_user(request)))
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        analysis = records.get_cv_analysis(active_request_user(request), str(pk))
        return Response(self.get_serializer(analysis).data)

    @extend_schema(
        request=CVAnalysisCreateSerializer,
        responses={201: CVAnalysisResultSerializer},
        description="Run a synchronous ATS analysis of one owned CV against a role and level.",
    )
    def create(self, request: Request) -> Response:
        serializer = CVAnalysisCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        analysis = cv_review.create_analysis(
            active_request_user(request), data["cv"], data["role_profile_id"], data["level"]
        )
        return Response(self.get_serializer(analysis).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=CVRewriteRequestSerializer,
        responses={200: CVRewriteSerializer},
        description="Rewrite one bullet with the local model, validated; nothing is stored.",
    )
    @action(detail=True, methods=("post",))
    def rewrite(self, request: Request, pk: str | None = None) -> Response:
        serializer = CVRewriteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = cv_review.request_rewrite(
            active_request_user(request), str(pk), serializer.validated_data["bullet"]
        )
        return Response(CVRewriteSerializer(result).data)

    @extend_schema(
        request=None,
        responses={200: CVRewriteSerializer},
        description="Propose a validated professional summary; nothing is stored.",
    )
    @action(detail=True, methods=("post",))
    def summary(self, request: Request, pk: str | None = None) -> Response:
        result = cv_review.request_summary(active_request_user(request), str(pk))
        return Response(CVRewriteSerializer(result).data)

    @extend_schema(
        request=CVDraftUpdateSerializer,
        responses={200: CVAnalysisResultSerializer},
        description="Record one choice in the CV draft: a bullet, a missing skill or the summary.",
    )
    @action(detail=True, methods=("patch",))
    def draft(self, request: Request, pk: str | None = None) -> Response:
        serializer = CVDraftUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        analysis = cv_review.update_draft(
            active_request_user(request), str(pk), serializer.validated_data
        )
        return Response(self.get_serializer(analysis).data)

    @extend_schema(
        parameters=[OpenApiParameter("file_format", enum=("pdf", "docx"), default="pdf")],
        responses={(200, "application/octet-stream"): OpenApiTypes.BINARY},
        description="Download the CV draft as an ATS-friendly PDF or DOCX; nothing is stored. "
        "X-CV-Placeholders counts unresolved [X] placeholders (a warning, not a refusal); "
        "X-CV-Missing-Sections lists sections the level requires that the CV lacks.",
    )
    @action(detail=True, methods=("get",))
    def generate(self, request: Request, pk: str | None = None) -> FileResponse:
        serializer = CVGenerateSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        file_format = serializer.validated_data["file_format"]
        generated, file_name = cv_review.generate_file(
            active_request_user(request), str(pk), file_format
        )
        response = FileResponse(
            BytesIO(generated.content),
            as_attachment=True,
            filename=file_name,
            content_type=cv_review.MIME_TYPES[file_format],
        )
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        response["X-CV-Placeholders"] = str(generated.placeholders)
        response["X-CV-Missing-Sections"] = ",".join(generated.missing_sections)
        return response

    @extend_schema(
        request=CVGenerateSerializer,
        responses={201: CVSerializer},
        description="Save the generated file as a new CV version (not primary). The UI asks "
        "for explicit confirmation first.",
    )
    @action(detail=True, methods=("post",), url_path="save-cv")
    def save_cv(self, request: Request, pk: str | None = None) -> Response:
        serializer = CVGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cv = cv_review.save_as_cv(
            active_request_user(request), str(pk), serializer.validated_data["file_format"]
        )
        return Response(CVSerializer(cv).data, status=status.HTTP_201_CREATED)


class CVReviewRoleViewSet(GenericViewSet[Any]):
    serializer_class = RoleProfileSerializer
    pagination_class = None

    def list(self, request: Request) -> Response:
        roles = cv_review.list_roles(active_request_user(request))
        return Response(self.get_serializer(roles, many=True).data)
