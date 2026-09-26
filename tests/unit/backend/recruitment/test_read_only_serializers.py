import pytest
from rest_framework import serializers

from backend.apps.recruitment.api.application_status_history_serializers import (
    ApplicationStatusHistoryReadSerializer,
)
from backend.apps.recruitment.api.applications_serializers import ApplicationReadSerializer
from backend.apps.recruitment.api.interviews_serializers import InterviewReadSerializer

pytestmark = pytest.mark.unit

READ_ONLY_SERIALIZERS: list[type[serializers.ModelSerializer]] = [
    ApplicationReadSerializer,
    ApplicationStatusHistoryReadSerializer,
    InterviewReadSerializer,
]


@pytest.mark.parametrize("serializer_class", READ_ONLY_SERIALIZERS)
def test_every_field_is_read_only(serializer_class: type[serializers.ModelSerializer]) -> None:
    fields = serializer_class().fields
    assert fields
    assert all(field.read_only for field in fields.values())
