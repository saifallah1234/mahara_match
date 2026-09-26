from django.core.validators import RegexValidator
from django.db import models

from backend.common.models import UUIDTimestampedModel


class OrganizationType(models.TextChoices):
    COMPANY = "COMPANY", "Company"
    SUBSIDIARY = "SUBSIDIARY", "Subsidiary"
    TRAINING_PROVIDER = "TRAINING_PROVIDER", "Training provider"
    ANETI = "ANETI", "ANETI"
    MINISTRY = "MINISTRY", "Ministry"


class VerificationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    VERIFIED = "VERIFIED", "Verified"
    REJECTED = "REJECTED", "Rejected"


class Organization(UUIDTimestampedModel):
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subsidiaries",
    )
    type = models.CharField(
        max_length=30,
        choices=OrganizationType.choices,
    )
    legal_name = models.CharField(max_length=255)
    registration_number = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
    )
    description = models.TextField(blank=True)
    website_url = models.TextField(blank=True)
    logo_uri = models.TextField(blank=True)
    matricule_fiscal = models.CharField(
        max_length=13,
        unique=True,
        validators=[
            RegexValidator(
                regex=r"^\d{7}[A-Z]\d{3}\d{2}$",
                message="Enter a valid 13-character Tunisian matricule fiscal.",
            )
        ],
    )
    governorate = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=100, blank=True)
    address_line = models.CharField(max_length=255, blank=True)
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "organizations"
        ordering = ("legal_name", "id")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(type=OrganizationType.SUBSIDIARY)
                | models.Q(parent_id__isnull=True),
                name="organizations_only_subsidiaries_have_parent",
            )
        ]

    def __str__(self) -> str:
        return self.legal_name
