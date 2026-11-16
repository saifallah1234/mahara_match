# Placement: backend/apps/recruitment/services/indicators.py
"""Aggregate recruitment counts for reporting. Numbers only: no IDs, names or rows.

Counted offers are published, non-deleted offers; applications and hires are those
made to counted offers. Governorates are returned as stored (stripped).
"""

from collections import Counter

from django.db.models import Count, Q, QuerySet

from backend.apps.recruitment.models import (
    Application,
    ApplicationStatus,
    JobOffer,
    JobOfferStatus,
    OfferSkill,
)


def _counted_offers() -> QuerySet[JobOffer]:
    return JobOffer.objects.filter(status=JobOfferStatus.PUBLISHED, deleted_at__isnull=True)


def recruitment_counts_by_governorate() -> dict[str, Counter[str]]:
    """``{"offers"|"applications"|"hires": Counter(governorate -> count)}``."""
    counts: dict[str, Counter[str]] = {
        "offers": Counter(),
        "applications": Counter(),
        "hires": Counter(),
    }
    for row in _counted_offers().values("governorate").annotate(n=Count("id")):
        counts["offers"][row["governorate"].strip()] += row["n"]
    applications = (
        Application.objects.filter(offer__in=_counted_offers())
        .values("offer__governorate")
        .annotate(n=Count("id"), hires=Count("id", filter=Q(status=ApplicationStatus.HIRED)))
    )
    for row in applications:
        governorate = row["offer__governorate"].strip()
        counts["applications"][governorate] += row["n"]
        counts["hires"][governorate] += row["hires"]
    return counts


def offer_demand_by_skill() -> Counter[str]:
    """Skill name -> number of counted offers listing it."""
    rows = (
        OfferSkill.objects.filter(offer__in=_counted_offers())
        .values("skill__canonical_name")
        .annotate(n=Count("offer", distinct=True))
    )
    return Counter({row["skill__canonical_name"]: row["n"] for row in rows})
