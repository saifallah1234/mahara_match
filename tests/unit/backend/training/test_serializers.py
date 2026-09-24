import uuid

import pytest

from backend.apps.training.api.enrollments_serializers import TrainingEnrollmentSerializer
from backend.apps.training.api.programs_serializers import TrainingProgramSerializer


@pytest.mark.django_db
def test_training_program_serializer_validation():
    payload = {
        "organization_id": str(uuid.uuid4()),
        "title": "Machine Learning Foundations",
        "description": "Introductory course to ML",
        "level": "BEGINNER",
        "delivery_mode": "ONLINE",
        "status": "DRAFT",
        "is_paid": False,
    }
    serializer = TrainingProgramSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["title"] == "Machine Learning Foundations"


@pytest.mark.django_db
def test_training_enrollment_serializer_read_only_fields():
    payload = {
        "session": str(uuid.uuid4()),
        "candidate_id": str(uuid.uuid4()),
        "completion_rate": 50.0,
    }
    serializer = TrainingEnrollmentSerializer(data=payload)
    assert serializer.is_valid(), serializer.errors
