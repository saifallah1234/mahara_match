import time

from django.core.management.base import BaseCommand

from backend.apps.assistant.services.interview_jobs import run_one


class Command(BaseCommand):
    help = "Run leased application-side interview work. Never starts an EC2 instance."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        while True:
            worked = run_one()
            if options["once"]:
                break
            if not worked:
                time.sleep(1)
