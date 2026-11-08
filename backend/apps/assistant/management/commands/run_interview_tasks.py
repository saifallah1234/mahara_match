import time

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.apps.assistant.services.interview_contracts import InterviewUnavailable
from backend.apps.assistant.services.interview_jobs import run_one, speech_provider


class Command(BaseCommand):
    help = "Run leased application-side interview work. Never starts an EC2 instance."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        # Fail at startup, not on a candidate's first answer (missing extra or model).
        for kind, name in (("stt", settings.STT_PROVIDER), ("tts", settings.TTS_PROVIDER)):
            try:
                speech_provider(kind)
            except InterviewUnavailable as exc:
                raise CommandError(f"{kind.upper()} provider '{name}' unavailable: {exc}") from exc
        while True:
            worked = run_one()
            if options["once"]:
                break
            if not worked:
                time.sleep(1)
