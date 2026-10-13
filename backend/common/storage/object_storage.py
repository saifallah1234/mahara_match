from collections.abc import Iterator
from io import BytesIO
from typing import cast
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from minio import Minio


def _configuration() -> tuple[Minio, str]:
    values = (
        settings.MINIO_ENDPOINT,
        settings.MINIO_BUCKET,
        settings.MINIO_ACCESS_KEY,
        settings.MINIO_SECRET_KEY,
    )
    if not all(values):
        raise ImproperlyConfigured("Object storage is not configured.")

    endpoint = cast(str, settings.MINIO_ENDPOINT)
    bucket = cast(str, settings.MINIO_BUCKET)
    access_key = cast(str, settings.MINIO_ACCESS_KEY)
    secret_key = cast(str, settings.MINIO_SECRET_KEY)
    scheme = "https" if settings.MINIO_USE_SSL else "http"
    parsed = urlsplit(endpoint if "://" in endpoint else f"{scheme}://{endpoint}")
    if not parsed.netloc or parsed.path not in {"", "/"}:
        raise ImproperlyConfigured("MINIO_ENDPOINT is invalid.")

    return (
        Minio(
            parsed.netloc,
            access_key=access_key,
            secret_key=secret_key,
            secure=parsed.scheme == "https",
        ),
        bucket,
    )


def upload_object(object_key: str, content: bytes, mime_type: str) -> None:
    client, bucket = _configuration()
    client.put_object(
        bucket,
        object_key,
        BytesIO(content),
        length=len(content),
        content_type=mime_type,
    )


def download_object(object_key: str) -> bytes:
    client, bucket = _configuration()
    response = client.get_object(bucket, object_key)
    try:
        content = response.read(settings.DOCUMENT_MAX_UPLOAD_BYTES + 1)
    finally:
        response.close()
        response.release_conn()
    if len(content) > settings.DOCUMENT_MAX_UPLOAD_BYTES:
        raise ValueError("Stored document exceeds the download limit.")
    return content


def delete_object(object_key: str) -> None:
    client, bucket = _configuration()
    client.remove_object(bucket, object_key)


def object_metadata(object_key: str) -> tuple[int, str]:
    client, bucket = _configuration()
    metadata = client.stat_object(bucket, object_key)
    return int(metadata.size or 0), metadata.content_type or "application/octet-stream"


def read_bounded(object_key: str, limit: int) -> bytes:
    client, bucket = _configuration()
    response = client.get_object(bucket, object_key)
    try:
        content = response.read(limit + 1)
        if len(content) > limit:
            raise ValueError("Media exceeds the configured read limit.")
        return content
    finally:
        response.close()
        response.release_conn()


def stream_object(object_key: str) -> Iterator[bytes]:
    client, bucket = _configuration()
    response = client.get_object(bucket, object_key)
    try:
        yield from response.stream(64 * 1024)
    finally:
        response.close()
        response.release_conn()
