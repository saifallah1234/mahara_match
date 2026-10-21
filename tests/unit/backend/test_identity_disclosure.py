# Placement: tests/unit/backend/test_identity_disclosure.py
import pytest
from rest_framework import serializers

from backend.apps.recruitment.api.applications_serializers import ApplicationReadSerializer
from backend.apps.training.api.enrollments_serializers import TrainingEnrollmentReadSerializer

pytestmark = pytest.mark.unit

# ADR 0001: the receiving organization sees first and last name only. No e-mail, no phone.
DISCLOSED_SOURCES = {"candidate.user.first_name", "candidate.user.last_name"}


@pytest.mark.parametrize(
    "serializer_class", [ApplicationReadSerializer, TrainingEnrollmentReadSerializer]
)
def test_candidate_identity_is_limited_to_names(
    serializer_class: type[serializers.ModelSerializer],
) -> None:
    fields = serializer_class().fields
    identity_sources = {
        field.source
        for name, field in fields.items()
        if name.startswith("candidate_") and name != "candidate_id"
    }
    assert identity_sources == DISCLOSED_SOURCES
    assert not {"email", "phone", "phone_number"} & set(fields)
