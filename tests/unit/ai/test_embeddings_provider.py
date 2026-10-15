import json
from io import BytesIO
from typing import Any
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest

from ai.llm.providers.embeddings import (
    EmbeddingConfig,
    EmbeddingDimensionError,
    EmbeddingUnavailable,
    embed,
    embedding_config,
)

pytestmark = pytest.mark.unit

CONFIG = EmbeddingConfig(model="bge-m3", dimensions=2, base_url="http://ollama:11434")
URLOPEN = "ai.llm.providers.embeddings.urlopen"


def _response(vectors: list[list[float]]) -> BytesIO:
    return BytesIO(json.dumps({"embeddings": vectors}).encode())


def _http_error(code: int) -> HTTPError:
    return HTTPError("http://ollama:11434/api/embed", code, "error", {}, None)  # type: ignore[arg-type]


def test_config_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_MODEL", "nomic-embed-text")
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "768")
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://host:11434/")
    assert embedding_config() == EmbeddingConfig("nomic-embed-text", 768, "http://host:11434")


def test_config_rejects_non_integer_dimensions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("EMBEDDING_DIMENSIONS", "large")
    with pytest.raises(ValueError, match="EMBEDDING_DIMENSIONS"):
        embedding_config()


def test_texts_are_sent_in_batches_and_order_is_kept() -> None:
    requests: list[dict[str, Any]] = []

    def fake_urlopen(request: Any, timeout: float) -> BytesIO:
        payload = json.loads(request.data)
        requests.append(payload)
        return _response([[float(len(text)), 0.0] for text in payload["input"]])

    with patch(URLOPEN, side_effect=fake_urlopen):
        vectors = embed(["a", "bb", "ccc"], CONFIG, batch_size=2)

    assert [payload["input"] for payload in requests] == [["a", "bb"], ["ccc"]]
    assert {payload["model"] for payload in requests} == {"bge-m3"}
    assert vectors == [[1.0, 0.0], [2.0, 0.0], [3.0, 0.0]]


@pytest.mark.parametrize(
    "error", [_http_error(503), _http_error(429), URLError("refused"), TimeoutError()]
)
def test_transient_failures_are_retried(error: Exception) -> None:
    delays: list[float] = []
    with patch(URLOPEN, side_effect=[error, _response([[1.0, 2.0]])]):
        vectors = embed(["query"], CONFIG, backoff=0.5, sleep=delays.append)
    assert vectors == [[1.0, 2.0]]
    assert delays == [0.5]


def test_exhausted_retries_raise_unavailable() -> None:
    delays: list[float] = []
    with (
        patch(URLOPEN, side_effect=URLError("refused")) as urlopen,
        pytest.raises(EmbeddingUnavailable),
    ):
        embed(["query"], CONFIG, attempts=3, backoff=1.0, sleep=delays.append)
    assert urlopen.call_count == 3
    assert delays == [1.0, 2.0]


def test_permanent_http_error_is_not_retried() -> None:
    with (
        patch(URLOPEN, side_effect=_http_error(404)) as urlopen,
        pytest.raises(EmbeddingUnavailable),
    ):
        embed(["query"], CONFIG, sleep=lambda _: None)
    assert urlopen.call_count == 1


def test_malformed_response_is_unavailable() -> None:
    with (
        patch(URLOPEN, return_value=BytesIO(b'{"embeddings": []}')),
        pytest.raises(EmbeddingUnavailable),
    ):
        embed(["query"], CONFIG)


def test_dimension_mismatch_raises_and_is_not_a_degradable_outage() -> None:
    with (
        patch(URLOPEN, return_value=_response([[1.0, 2.0, 3.0]])),
        pytest.raises(EmbeddingDimensionError, match="3-dimension"),
    ):
        embed(["query"], CONFIG)
    assert not issubclass(EmbeddingDimensionError, EmbeddingUnavailable)
