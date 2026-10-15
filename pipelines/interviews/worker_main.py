"""Explicit live worker entry point. Never starts an EC2 instance."""

import logging
import os
import time
from pathlib import Path

from pipelines.interviews.latentsync import LatentSyncRunner
from pipelines.interviews.queue import SQSQueue
from pipelines.interviews.storage import WorkerStorage
from pipelines.interviews.worker import InterviewWorker, worker_lock


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    if os.getenv("INTERVIEW_ALLOW_LIVE_AWS") != "true":
        raise ValueError("Live AWS requires explicit deployment enablement after approval.")
    import boto3  # type: ignore[import-untyped]
    from minio import Minio

    runner = LatentSyncRunner(
        checkout=Path(os.environ["LATENTSYNC_CHECKOUT"]),
        conda=os.environ["LATENTSYNC_CONDA"],
        environment="latentsync",
        config=Path(os.environ["LATENTSYNC_CONFIG"]),
        checkpoint=Path(os.environ["LATENTSYNC_CHECKPOINT"]),
        revision=os.environ["LATENTSYNC_REVISION"],
        fps_verified=os.getenv("LATENTSYNC_FPS_VERIFIED") == "true",
        ffmpeg=os.getenv("INTERVIEW_FFMPEG", "ffmpeg"),
        inference_timeout=int(os.getenv("INTERVIEW_INFERENCE_TIMEOUT_SECONDS", "3600")),
    )
    client = boto3.client("sqs", region_name=os.environ["INTERVIEW_AWS_REGION"])
    queues = [
        SQSQueue(client, os.environ[name])
        for name in (
            "INTERVIEW_PRIORITY_QUEUE_URL",
            "INTERVIEW_BACKGROUND_QUEUE_URL",
            "INTERVIEW_STATUS_QUEUE_URL",
        )
    ]
    storage = WorkerStorage(
        Minio(
            os.environ["MINIO_ENDPOINT"],
            access_key=os.environ["MINIO_ACCESS_KEY"],
            secret_key=os.environ["MINIO_SECRET_KEY"],
            secure=True,
        ),
        os.environ["MINIO_BUCKET"],
    )
    worker = InterviewWorker(
        priority=queues[0],
        background=queues[1],
        status=queues[2],
        storage=storage,
        avatar_dir=Path(os.environ["LATENTSYNC_AVATAR_DIR"]),
        runner=runner,
        ffmpeg=os.getenv("INTERVIEW_FFMPEG", "ffmpeg"),
        visibility=int(os.getenv("INTERVIEW_VISIBILITY_SECONDS", "900")),
        heartbeat=float(os.getenv("INTERVIEW_HEARTBEAT_SECONDS", "60")),
    )
    with worker_lock(
        Path(os.getenv("INTERVIEW_WORKER_LOCK", "/var/lib/mahara-interview/worker.lock"))
    ):
        logging.getLogger(__name__).info(
            "Interview worker started; polling priority and background queues."
        )
        while True:
            if not worker.run_one():
                # Long poll priority when idle; background never delays known priority work.
                message = worker.priority.receive(wait=20, visibility=worker.visibility)
                if message:
                    try:
                        worker.process(worker.priority, message)
                    except Exception:
                        logging.getLogger(__name__).exception(
                            "Interview request retained after worker failure."
                        )
                else:
                    time.sleep(1)


if __name__ == "__main__":
    main()
