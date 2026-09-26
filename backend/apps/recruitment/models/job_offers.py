import uuid
from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import F, Q


class JobOfferStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    PUBLISHED = "PUBLISHED", "Published"
    PAUSED = "PAUSED", "Paused"
    CLOSED = "CLOSED", "Closed"
    ARCHIVED = "ARCHIVED", "Archived"


class JobOffer(models.Model):
    objects: models.Manager["JobOffer"]
    id: Any = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization: Any = models.ForeignKey(  # type: ignore[misc]
        "identity.Organization",
        on_delete=models.PROTECT,
        related_name="job_offers",
    )
    created_by: Any = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_job_offers",
    )
    # ponytail: keep this ID unattached until imports.DataSource is implemented.
    source_id: Any = models.UUIDField(null=True, blank=True)
    # Q16: missing-ID policy undecided; NULL means "no external id".
    external_id: Any = models.CharField(  # noqa: DJ001 - NULL distinguishes missing external IDs.
        max_length=255, null=True, blank=True
    )
    title: Any = models.CharField(max_length=200)
    description: Any = models.TextField()
    # Q24: enum values for these three are not defined in the data model.
    contract_type: Any = models.CharField(max_length=30, blank=True)
    work_mode: Any = models.CharField(max_length=30, blank=True)
    experience_level: Any = models.CharField(max_length=30, blank=True)
    # Q24: source says VARCHAR without a length; lengths below are provisional.
    country_code: Any = models.CharField(max_length=2, blank=True)
    governorate: Any = models.CharField(max_length=100, blank=True)
    city: Any = models.CharField(max_length=100, blank=True)
    # Q10: NO currency field yet, although DM section 7 requires one when a salary is set.
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
    # Q11: source says VARCHAR(50), which is too short for most URLs. Kept as specified.
    offer_url: Any = models.CharField(max_length=50, blank=True)
    # Q11: nullability/cardinality undecided. Source spells the second one "requiered_languages".
    description_language: Any = models.ForeignKey(  # type: ignore[misc]
        "taxonomy.Language",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="described_job_offers",
    )
    required_language: Any = models.ForeignKey(  # type: ignore[misc]
        "taxonomy.Language",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requiring_job_offers",
    )
    education_level: Any = models.ForeignKey(  # type: ignore[misc]
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
        ]

    def __str__(self) -> str:
        return self.title
