# Placement: backend/apps/reporting/services/indicators.py
"""Ministry indicators: demo counts combined from recruitment and training aggregates.

These are not approved KPIs (Q20 stays open). Only aggregate numbers leave this module.
"""

from typing import Any

from backend.apps.identity.models import User
from backend.apps.identity.services.access import require_permission
from backend.apps.recruitment.services.indicators import (
    offer_demand_by_skill,
    recruitment_counts_by_governorate,
)
from backend.apps.reporting.services.contracts import ReportingPermissionCode
from backend.apps.training.services.indicators import (
    program_counts_by_governorate,
    program_supply_by_skill,
)

NOT_SPECIFIED = "Non précisé"


def ministry_indicators(actor: User) -> dict[str, list[dict[str, Any]]]:
    require_permission(actor, ReportingPermissionCode.READ_INDICATORS)
    metrics = {**recruitment_counts_by_governorate(), "trainings": program_counts_by_governorate()}
    regions: dict[str, dict[str, Any]] = {}
    for metric, counts in metrics.items():
        for governorate, count in counts.items():
            label = governorate or NOT_SPECIFIED
            row = regions.setdefault(label, {"governorate": label, **dict.fromkeys(metrics, 0)})
            row[metric] += count
    demand, supply = offer_demand_by_skill(), program_supply_by_skill()
    return {
        # "Not specified" sorts last so the named governorates read first.
        "regions": sorted(
            regions.values(), key=lambda r: (r["governorate"] == NOT_SPECIFIED, r["governorate"])
        ),
        "skill_gaps": [
            {"skill": skill, "offer_demand": demand[skill], "training_supply": supply[skill]}
            for skill in sorted(demand.keys() | supply.keys())
        ],
    }
