import uuid
from typing import Any

from django.conf import settings
from django.core.validators import URLValidator
from django.db import models
from django.db.models import F, Q

from backend.apps.candidates.models.entities import WorkMode


class JobOfferStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    PAUSED = "PAUSED", "Paused"
    CLOSED = "CLOSED", "Closed"
    ARCHIVED = "ARCHIVED", "Archived"


class JobOffer(models.Model):
    objects: models.Manager["JobOffer"]
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization: Any = models.ForeignKey(
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="job_offers",
    )
    company_name: Any = models.CharField(max_length=255, blank=True)
    created_by: Any = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_job_offers",
    )
    source: Any = models.ForeignKey(
        "imports.DataSource", on_delete=models.PROTECT, null=True, blank=True
    )
    source_id: uuid.UUID | None
    # Automated imports require an external ID; manual employer offers may omit one.
    external_id: Any = models.CharField(  # noqa: DJ001 - NULL distinguishes missing external IDs.
        max_length=255, null=True, blank=True
    )
    title: Any = models.CharField(max_length=200)
    description: Any = models.TextField()
    # Q24: enum values for these three are not defined in the data model.
    contract_type: Any = models.CharField(max_length=30, blank=True)
    work_mode: Any = models.CharField(max_length=30, choices=WorkMode.choices, blank=True)
    experience_level: Any = models.CharField(max_length=30, blank=True)
    # Q24: source says VARCHAR without a length; lengths below are provisional.
    country_code: Any = models.CharField(max_length=2, blank=True)
    governorate: Any = models.CharField(max_length=100, blank=True)
    city: Any = models.CharField(max_length=100, blank=True)
    # Salaries are always TND (Q10).
    min_salary: Any = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_salary: Any = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    application_deadline: Any = models.DateField(null=True, blank=True)
    status: Any = models.CharField(
        max_length=20,
        choices=JobOfferStatus.choices,
        default=JobOfferStatus.DRAFT,
        db_index=True,
    )
    published_at: Any = models.DateTimeField(null=True, blank=True)
    closed_at: Any = models.DateTimeField(null=True, blank=True)
    offer_url: Any = models.URLField(
        max_length=500, blank=True, validators=[URLValidator(schemes=["https"])]
    )
    description_language: Any = models.ForeignKey(
        "taxonomy.Language",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="described_job_offers",
    )
    education_level: Any = models.ForeignKey(
        "taxonomy.EducationLevel",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="job_offers",
    )
    # False = external application, no application/interview tracking (Q12).
    # No default on purpose: the source does not define one.
    easy_apply: Any = models.BooleanField()
    organization_id: uuid.UUID
    created_at: Any = models.DateTimeField(auto_now_add=True)
    updated_at: Any = models.DateTimeField(auto_now=True)
    # DM section 7: offers with application history must be soft-deleted.
    deleted_at: Any = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "job_offers"
        ordering = ("created_at", "id")
        constraints = [
            models.CheckConstraint(
                condition=Q(source_id__isnull=True)
                | (Q(external_id__isnull=False) & ~Q(external_id="")),
                name="job_offers_import_has_external_id",
            ),
            models.UniqueConstraint(
                fields=["source_id", "external_id"],
                condition=Q(external_id__isnull=False),
                name="job_offers_source_external_id_unique",
            ),
            models.CheckConstraint(
                condition=(
                    Q(min_salary__isnull=True)
                    | Q(max_salary__isnull=True)
                    | Q(max_salary__gte=F("min_salary"))
                ),
                name="job_offers_max_salary_gte_min_salary",
            ),
            models.CheckConstraint(
                condition=Q(min_salary__isnull=True) | Q(min_salary__gte=0),
                name="job_offers_min_salary_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(max_salary__isnull=True) | Q(max_salary__gte=0),
                name="job_offers_max_salary_nonnegative",
            ),
        ]

    def __str__(self) -> str:
        return self.title
