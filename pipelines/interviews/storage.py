"""Standalone private MinIO transport for the worker, independent of Django settings."""

import json
from io import BytesIO
from typing import Any

from minio.error import S3Error


class WorkerStorage:
    def __init__(self, client: Any, bucket: str):
        self.client, self.bucket = client, bucket

    def read(self, key: str, limit: int) -> bytes:
        response = self.client.get_object(self.bucket, key)
        try:
            content = response.read(limit + 1)
            if len(content) > limit:
                raise ValueError("Worker object exceeds limit.")
            return content
        finally:
            response.close()
            response.release_conn()

    def write(self, key: str, content: bytes, mime: str) -> None:
        self.client.put_object(
            self.bucket, key, BytesIO(content), length=len(content), content_type=mime
        )

    def manifest(self, key: str) -> dict | None:
        try:
            return json.loads(self.read(key, 64 * 1024))
        except S3Error as exc:
            if exc.code != "NoSuchKey":
                raise
            return None
