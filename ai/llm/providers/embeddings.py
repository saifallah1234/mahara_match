"""Ollama embedding client shared by indexing, evaluation and query-time retrieval."""

from __future__ import annotations

import json
import os
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class EmbeddingUnavailable(RuntimeError):
    """Ollama could not produce embeddings; callers may degrade to non-vector retrieval."""


class EmbeddingDimensionError(ValueError):
    """The model returned vectors of a size the index was not configured for."""


@dataclass(frozen=True)
class EmbeddingConfig:
    model: str
    dimensions: int
    base_url: str


def embedding_config(model: str | None = None, base_url: str | None = None) -> EmbeddingConfig:
    """Read the environment; explicit ``model``/``base_url`` (e.g. CLI flags) take precedence."""
    raw_dimensions = os.getenv("EMBEDDING_DIMENSIONS", "1024")
    try:
        dimensions = int(raw_dimensions)
    except ValueError as exc:
        raise ValueError(
            f"EMBEDDING_DIMENSIONS must be an integer, got {raw_dimensions!r}."
        ) from exc
    if dimensions < 1:
        raise ValueError("EMBEDDING_DIMENSIONS must be positive.")
    model = model or os.environ.get("EMBEDDING_MODEL") or "bge-m3"
    base_url = base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
    return EmbeddingConfig(model=model, dimensions=dimensions, base_url=base_url.rstrip("/"))


def embed(
    texts: Sequence[str],
    config: EmbeddingConfig | None = None,
    *,
    batch_size: int = 16,
    timeout: float = 120,
    attempts: int = 3,
    backoff: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
) -> list[list[float]]:
    """Embed ``texts`` in order, retrying transient Ollama failures per batch."""
    if batch_size < 1 or attempts < 1:
        raise ValueError("batch_size and attempts must be positive.")
    config = config or embedding_config()
    vectors: list[list[float]] = []
    for start in range(0, len(texts), batch_size):
        batch = list(texts[start : start + batch_size])
        vectors.extend(_embed_with_retries(config, batch, timeout, attempts, backoff, sleep))
    wrong = [len(vector) for vector in vectors if len(vector) != config.dimensions]
    if wrong:
        raise EmbeddingDimensionError(
            f"Model {config.model!r} returned {wrong[0]}-dimension vectors; "
            f"EMBEDDING_DIMENSIONS is {config.dimensions}."
        )
    return vectors


def embed_query(text: str, config: EmbeddingConfig | None = None) -> list[float]:
    """Embed one interactive query with a short budget so a slow Ollama degrades quickly."""
    return embed([text], config, timeout=30, attempts=2)[0]


def is_transient(error: BaseException) -> bool:
    if isinstance(error, HTTPError):
        return error.code == 429 or 500 <= error.code < 600
    return isinstance(error, (URLError, TimeoutError, ConnectionError))


def _embed_with_retries(
    config: EmbeddingConfig,
    batch: list[str],
    timeout: float,
    attempts: int,
    backoff: float,
    sleep: Callable[[float], None],
) -> list[list[float]]:
    for attempt in range(1, attempts + 1):
        try:
            return _request(config, batch, timeout)
        except (HTTPError, URLError, TimeoutError, ConnectionError) as exc:
            if not is_transient(exc) or attempt == attempts:
                raise EmbeddingUnavailable(f"Could not get embeddings from Ollama: {exc}") from exc
            sleep(backoff * (2 ** (attempt - 1)))
    raise EmbeddingUnavailable("Ollama retries exhausted.")


def _request(config: EmbeddingConfig, batch: list[str], timeout: float) -> list[list[float]]:
    request = Request(
        f"{config.base_url}/api/embed",
        data=json.dumps({"model": config.model, "input": batch}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    vectors = payload.get("embeddings") if isinstance(payload, dict) else None
    if not isinstance(vectors, list) or len(vectors) != len(batch):
        raise EmbeddingUnavailable("Ollama returned an invalid embeddings response.")
    if any(not isinstance(vector, list) for vector in vectors):
        raise EmbeddingUnavailable("Ollama returned a malformed vector.")
    return vectors
