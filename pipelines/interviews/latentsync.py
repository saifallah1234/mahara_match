"""Standalone Python 3.10-compatible runner; trusted runtime configuration only."""

import logging
import math
import os
import shutil
import signal
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

from ai.speech.audio import decode_audio
from pipelines.interviews.queue import AVATARS

logger = logging.getLogger(__name__)


def resolve_avatar(root: Path, key: str) -> Path:
    if key not in AVATARS:
        raise ValueError("Unknown avatar.")
    root = root.expanduser().resolve()
    path = (root / AVATARS[key]).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Avatar missing or outside the allowlisted directory.")
    return path


def run_checked(
    command: list[str], *, cwd: Path, timeout: int, lease_check: Callable[[], None]
) -> bytes:
    deadline = time.monotonic() + timeout
    with subprocess.Popen(
        command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True
    ) as process:
        try:
            while True:
                lease_check()
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("Inference deadline exceeded.")
                try:
                    output, _ = process.communicate(timeout=min(1, remaining))
                    if process.returncode:
                        raise ValueError(
                            "Media subprocess failed: "
                            + output[-4000:].decode("utf-8", errors="replace")
                        )
                    return output
                except subprocess.TimeoutExpired:
                    continue
        except BaseException:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.wait()
            raise


def validate_video(content: bytes, duration_ms: int, ffmpeg: str) -> int:
    from tempfile import TemporaryDirectory

    decoded, audio_duration = decode_audio(content, ffmpeg)
    if abs(audio_duration - duration_ms) > 250:
        raise ValueError("Generated audio is truncated or has an unexpected duration.")
    with TemporaryDirectory(prefix="interview-video-check-") as scratch:
        source = Path(scratch) / "output.mp4"
        source.write_bytes(content)
        result = subprocess.run(
            [
                ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-format_whitelist",
                "mov,mp4,m4a,3gp,3g2,mj2",
                "-i",
                str(source),
                "-map",
                "0:v:0",
                "-an",
                "-progress",
                "pipe:1",
                "-f",
                "null",
                "-",
            ],
            check=True,
            timeout=60,
            capture_output=True,
        )
    times = [
        int(line.split("=", 1)[1])
        for line in result.stdout.decode().splitlines()
        if line.startswith("out_time_us=") and line.split("=", 1)[1].isdigit()
    ]
    if not times or abs(max(times) / 1000 - duration_ms) > 250:
        raise ValueError("Generated video duration does not cover the full audio.")
    return audio_duration


class LatentSyncRunner:
    def __init__(
        self,
        *,
        checkout: Path,
        conda: str,
        environment: str,
        config: Path,
        checkpoint: Path,
        revision: str,
        fps_verified: bool,
        ffmpeg: str = "ffmpeg",
        inference_timeout: int = 3600,
    ):
        self.checkout = checkout.expanduser().resolve()
        self.conda, self.environment, self.ffmpeg = conda, environment, ffmpeg
        if shutil.which(ffmpeg) is None:
            raise ValueError("Configure INTERVIEW_FFMPEG to an installed FFmpeg executable.")
        if not 1 <= inference_timeout < 43100:
            raise ValueError("Inference timeout must stay within the SQS processing limit.")
        self.inference_timeout = inference_timeout
        self.config, self.checkpoint = (
            config.expanduser().resolve(),
            checkpoint.expanduser().resolve(),
        )
        if not all(
            path.is_file()
            for path in (self.config, self.checkpoint, self.checkout / "scripts/inference.py")
        ):
            raise ValueError("Configure an existing LatentSync checkout, config and checkpoint.")
        actual = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=self.checkout, text=True
        ).strip()
        if not revision or actual != revision or not fps_verified:
            raise ValueError("Verify and pin the deployed revision and its 15 FPS patch first.")

    def __call__(
        self,
        avatar: Path,
        audio: bytes,
        duration_ms: int,
        scratch: Path,
        lease_check: Callable[[], None],
    ) -> bytes:
        normalized, measured = decode_audio(audio, self.ffmpeg)
        if abs(measured - duration_ms) > 100:
            raise ValueError("Input duration does not match audio.")
        audio_path, timeline, output = (
            scratch / "audio.wav",
            scratch / "source.mp4",
            scratch / "output.mp4",
        )
        audio_path.write_bytes(normalized)
        logger.info("Preparing avatar timeline for %s ms audio.", duration_ms)
        # Extend original motion forward; never loop generated speech.
        length = math.ceil(duration_ms * 15 / 1000) / 15 + 1 / 15
        run_checked(
            [
                self.ffmpeg,
                "-nostdin",
                "-v",
                "error",
                "-stream_loop",
                "-1",
                "-i",
                str(avatar),
                "-map",
                "0:v:0",
                "-an",
                "-t",
                str(length),
                "-vf",
                "fps=15",
                "-c:v",
                "libx264",
                str(timeline),
            ],
            cwd=scratch,
            timeout=180,
            lease_check=lease_check,
        )
        logger.info("Starting LatentSync inference.")
        run_checked(
            [
                self.conda,
                "run",
                "--no-capture-output",
                "-n",
                self.environment,
                "python",
                "-m",
                "scripts.inference",
                "--unet_config_path",
                str(self.config),
                "--inference_ckpt_path",
                str(self.checkpoint),
                "--video_path",
                str(timeline),
                "--audio_path",
                str(audio_path),
                "--video_out_path",
                str(output),
                "--temp_dir",
                str(scratch / "inference"),
                "--inference_steps",
                "8",
                "--guidance_scale",
                "1.5",
                "--enable_deepcache",
            ],
            cwd=self.checkout,
            timeout=self.inference_timeout,
            lease_check=lease_check,
        )
        content = output.read_bytes()
        validate_video(content, duration_ms, self.ffmpeg)
        return content
