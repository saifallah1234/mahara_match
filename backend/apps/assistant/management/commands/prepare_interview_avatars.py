import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from backend.apps.assistant.services.interview_contracts import AVATARS
from backend.apps.assistant.services.interview_media import avatar_path


class Command(BaseCommand):
    help = "Prepare separate muted forward-loop avatars locally; never transfer originals."

    def handle(self, *args, **options):
        destination = Path(settings.MOCK_INTERVIEW_DERIVATIVE_DIR).resolve()
        sources = {key: avatar_path(key) for key in AVATARS}
        destination.mkdir(parents=True, exist_ok=True)
        for key, source in sources.items():
            target = destination / f"{key}.mp4"
            if target.resolve() in sources.values():
                raise CommandError("Derivative must not overwrite an original.")
            with TemporaryDirectory(prefix="avatar-", dir=destination) as scratch:
                output = Path(scratch) / "muted.mp4"
                try:
                    subprocess.run(
                        [
                            settings.INTERVIEW_FFMPEG,
                            "-nostdin",
                            "-v",
                            "error",
                            "-i",
                            str(source),
                            "-map",
                            "0:v:0",
                            "-an",
                            "-vf",
                            "fps=15",
                            "-c:v",
                            "libx264",
                            "-preset",
                            "fast",
                            "-movflags",
                            "+faststart",
                            str(output),
                        ],
                        check=True,
                        timeout=180,
                        capture_output=True,
                    )
                except (OSError, subprocess.SubprocessError) as exc:
                    raise CommandError(f"Cannot prepare avatar {key}.") from exc
                output.replace(target)
            self.stdout.write(f"Prepared {key}; review the forward-loop join before release.")
