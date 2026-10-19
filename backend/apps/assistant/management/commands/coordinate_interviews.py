import time

from django.core.management.base import BaseCommand

from backend.apps.assistant.services.interview_queue import configured_queues, coordinate_once


class Command(BaseCommand):
    help = "Publish durable video intents and ingest status; live AWS is disabled by default."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        queues = configured_queues()
        while True:
            try:
                coordinate_once(*queues)
            except Exception:
                self.stderr.write("Interview coordination failed; pending work is retained.")
            if options["once"]:
                return
            time.sleep(2)
