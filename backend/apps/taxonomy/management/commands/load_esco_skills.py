# Placement: backend/apps/taxonomy/management/commands/load_esco_skills.py
"""Load the ESCO skills extract into the skills table. Safe to run any number of times.

    uv run python backend/manage.py load_esco_skills --settings=backend.config.settings.development

Uses data/reference/esco/esco_skills_v1.2.1.csv.gz unless --file is given. Existing local
skills that match an ESCO preferred label exactly are linked (their name is kept).
"""

from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from backend.apps.taxonomy.services.esco import DEFAULT_EXTRACT, load_esco, read_extract


class Command(BaseCommand):
    help = "Load ESCO skills (fr/en/ar) and link matching local skills (idempotent)."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--file", type=Path, default=DEFAULT_EXTRACT)

    def handle(self, *args: Any, **options: Any) -> None:
        report = load_esco(read_extract(options["file"]))
        self.stdout.write(
            f"ESCO skills: {report.esco_total} in the file, {report.created} created, "
            f"{len(report.linked_local)} local skill(s) linked, {report.labels} ESCO labels."
        )
        for local, esco in report.linked_local:
            self.stdout.write(f"  linked: {local} -> {esco}")
