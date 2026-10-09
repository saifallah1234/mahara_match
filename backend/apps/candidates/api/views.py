from typing import Any

from drf_spectacular.utils import extend_schema
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
    CVAnalysisResultSerializer,
    CVSerializer,
    EducationSerializer,
    ExperienceSerializer,
    ProjectSerializer,
    RecruiterCandidateSerializer,
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
from backend.apps.candidates.services import discovery, records
from backend.apps.identity.api.common_permissions import active_request_user


class CandidateProfileViewSet(GenericViewSet[CandidateProfile]):
    serializer_class = CandidateProfileSerializer
    queryset = CandidateProfile.objects.none()

    @extend_schema(
        parameters=[CandidateDiscoveryQuerySerializer],
        responses=RecruiterCandidateSerializer(many=True),
        description="Redacted discovery for authorized recruiters. Only RECRUITERS opt-in profiles.",
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
        description="Redacted recruiter detail. Hidden, PUBLIC and inactive candidates return 404.",
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


class CVAnalysisResultViewSet(GenericViewSet[CVAnalysisResult]):
    queryset = CVAnalysisResult.objects.none()
    serializer_class = CVAnalysisResultSerializer

    def list(self, request: Request) -> Response:
        page = self.paginate_queryset(records.list_cv_analyses(active_request_user(request)))
        return self.get_paginated_response(self.get_serializer(page, many=True).data)

    def retrieve(self, request: Request, pk: str | None = None) -> Response:
        analysis = records.get_cv_analysis(active_request_user(request), str(pk))
        return Response(self.get_serializer(analysis).data)
