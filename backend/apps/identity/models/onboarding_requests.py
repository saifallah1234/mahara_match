from django.conf import settings
from django.db import models

from backend.common.models import UUIDTimestampedModel


class OnboardingRequest(UUIDTimestampedModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        APPROVED = "APPROVED", "Approved"
        REJECTED = "REJECTED", "Rejected"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="onboarding_request"
    )
    requested_role = models.CharField(max_length=50)
    organization_name = models.CharField(max_length=255)
    matricule_fiscal = models.CharField(max_length=13)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    organization = models.ForeignKey(
        "identity.Organization", on_delete=models.PROTECT, null=True, blank=True
    )

    class Meta:
        db_table = "onboarding_requests"
        ordering = ("created_at", "id")
