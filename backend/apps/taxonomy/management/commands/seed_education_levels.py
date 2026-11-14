# Placement: backend/apps/taxonomy/management/commands/seed_education_levels.py
"""Creates the Bac+N education level scale. Safe to run any number of times.

    uv run python backend/manage.py seed_education_levels --settings=backend.config.settings.development

Existing rows are never modified; only missing levels are created. The scale is
defined in backend/apps/taxonomy/services/education.py.
"""

from typing import Any

from django.core.management.base import BaseCommand

from backend.apps.taxonomy.services.education import EDUCATION_LEVELS, seed_education_levels


class Command(BaseCommand):
    help = "Create the base education levels (idempotent; never overwrites existing rows)."

    def handle(self, *args: Any, **options: Any) -> None:
        created = seed_education_levels()
        self.stdout.write(
            f"Education levels ready: {created} created, "
            f"{len(EDUCATION_LEVELS) - created} already present or slot taken."
        )
