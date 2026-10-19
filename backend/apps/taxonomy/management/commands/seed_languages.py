# Placement: backend/apps/taxonomy/management/commands/seed_languages.py
"""Creates the base rows of the languages table. Safe to run any number of times.

    uv run python backend/manage.py seed_languages --settings=backend.config.settings.development

Existing rows are never modified (names the team changed are kept); only missing
codes are created. Add a line to LANGUAGES to add a language.

Needs empty `__init__.py` files in `backend/apps/taxonomy/management/` and
`backend/apps/taxonomy/management/commands/`.
"""

from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand

# ISO 639-1 codes, English names. The import pipeline detects fr / en / ar.
LANGUAGES = (
    ("fr", "French"),
    ("en", "English"),
    ("ar", "Arabic"),
)


class Command(BaseCommand):
    help = "Create the base languages (idempotent; never overwrites existing rows)."

    def handle(self, *args: Any, **options: Any) -> None:
        language_model = apps.get_model("taxonomy", "Language")
        created = 0
        for code, name in LANGUAGES:
            _, was_created = language_model.objects.get_or_create(
                code=code, defaults={"name": name}
            )
            created += int(was_created)
        self.stdout.write(
            f"Languages ready: {created} created, {len(LANGUAGES) - created} already present."
        )
