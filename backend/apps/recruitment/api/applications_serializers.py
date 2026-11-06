from rest_framework import serializers

from backend.apps.candidates.api.serializers import RecruiterCandidateSerializer
from backend.apps.identity.api.applicant_serializers import ApplicantReadSerializer
from backend.apps.recruitment.models import Application, ApplicationStatus

APPLICATION_READ_FIELDS: tuple[str, ...] = (
    "id",
    "candidate_id",
    "candidate_first_name",
    "candidate_last_name",
    "offer_id",
    "offer_title",
    "cv_id",
    "status",
    "cover_letter",
    "applied_at",
    "withdrawn_at",
    "created_at",
    "updated_at",
)


class ApplicationReadSerializer(serializers.ModelSerializer[Application]):
    candidate_id = serializers.UUIDField(read_only=True)
    # Disclosed to the receiving organization only (ADR 0001).
    candidate_first_name = serializers.CharField(source="candidate.user.first_name", read_only=True)
    candidate_last_name = serializers.CharField(source="candidate.user.last_name", read_only=True)
    offer_id = serializers.UUIDField(read_only=True)
    offer_title = serializers.CharField(source="offer.title", read_only=True)
    cv_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Application
        fields = APPLICATION_READ_FIELDS
        read_only_fields = fields


class ApplicationReceiverReadSerializer(ApplicationReadSerializer):
    # Only for members of the receiving organization; candidates never see these (ADR 0001).
    applicant = ApplicantReadSerializer(source="candidate.user", read_only=True)
    candidate_profile = RecruiterCandidateSerializer(source="candidate", read_only=True)

    class Meta(ApplicationReadSerializer.Meta):
        fields = (*APPLICATION_READ_FIELDS, "applicant", "candidate_profile")
        read_only_fields = fields


class ApplicationSubmitSerializer(serializers.Serializer[dict[str, object]]):
    offer_id = serializers.UUIDField()
    cv_id = serializers.UUIDField()
    cover_letter = serializers.CharField(required=False, allow_blank=True)


class ApplicationTransitionSerializer(serializers.Serializer[dict[str, object]]):
    status = serializers.ChoiceField(choices=ApplicationStatus.values)
    reason = serializers.CharField(required=False, allow_blank=True)
