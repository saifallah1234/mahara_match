# Placement: backend/apps/identity/api/applicant_serializers.py
from rest_framework import serializers

from backend.apps.identity.models import User


class ApplicantReadSerializer(serializers.ModelSerializer[User]):
    """Identity disclosed to an organization that received an application or enrollment (ADR 0001)."""

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email")
        read_only_fields = fields
