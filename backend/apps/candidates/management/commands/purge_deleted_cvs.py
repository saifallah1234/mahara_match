from django.core.management.base import BaseCommand

from backend.apps.candidates.models import CV
from backend.apps.candidates.services.records import purge_cv_bytes
from backend.apps.documents.services.documents import DocumentStorageError


class Command(BaseCommand):
    help = "Retry purging eligible deleted CV files from object storage."

    def handle(self, *args: object, **options: object) -> None:
        purged = failed = 0
        for cv_id in (
            CV.objects.filter(deleted_at__isnull=False, bytes_purged_at__isnull=True)
            .values_list("id", flat=True)
            .iterator()
        ):
            try:
                purged += purge_cv_bytes(cv_id)
            except DocumentStorageError:
                failed += 1
        self.stdout.write(f"Purged {purged} CV files; {failed} storage failures.")
