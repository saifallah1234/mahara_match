# Placement: backend/apps/imports/management/commands/publish_imported_offers.py
"""Publish offers that imports before 2026-11-14 saved as DRAFT.

New imports are published directly; this one-off catch-up only touches DRAFT offers
owned by the import placeholder and import user. It also marks the placeholder
organization VERIFIED (unless an administrator rejected it), since candidates only
see offers of verified organizations.
"""

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from backend.apps.imports.services import batch_processing


class Command(BaseCommand):
    help = "Publish DRAFT offers left by earlier imports (use --dry-run to preview)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--dry-run", action="store_true", help="Only count the offers; write nothing."
        )

    def handle(self, *args: Any, **options: Any) -> None:
        if options["dry_run"]:
            count = batch_processing.count_previous_import_drafts()
            self.stdout.write(f"{count} imported DRAFT offer(s) would be published.")
            return
        count = batch_processing.publish_previous_imports()
        self.stdout.write(self.style.SUCCESS(f"Published {count} imported offer(s)."))
