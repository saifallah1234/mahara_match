from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest

from backend.apps.recruitment.api.application_status_history_serializers import (
    ApplicationStatusHistoryReadSerializer,
)
from backend.apps.recruitment.api.interviews_serializers import InterviewReadSerializer
from backend.apps.recruitment.models import ApplicationStatusHistory, Interview

pytestmark = pytest.mark.unit


def test_candidate_does_not_receive_recruiter_notes() -> None:
    candidate_id = uuid4()
    instance = SimpleNamespace(
        application=SimpleNamespace(candidate=SimpleNamespace(user_id=candidate_id)),
        reason="Internal reason",
        feedback="Internal feedback",
    )
    request = SimpleNamespace(user=SimpleNamespace(id=candidate_id))
    assert (
        ApplicationStatusHistoryReadSerializer(context={"request": request}).get_reason(
            cast(ApplicationStatusHistory, instance)
        )
        == ""
    )
    assert (
        InterviewReadSerializer(context={"request": request}).get_feedback(
            cast(Interview, instance)
        )
        == ""
    )
