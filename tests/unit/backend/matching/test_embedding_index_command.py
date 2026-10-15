import json
from contextlib import nullcontext
from io import BytesIO, StringIO
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management.base import CommandError

from backend.apps.matching.management.commands.index_retrieval import Command
from backend.apps.matching.services.embedding_index import EmbeddingDocument

pytestmark = pytest.mark.unit


def test_ollama_embed_uses_batch_api() -> None:
    response = BytesIO(b'{"embeddings": [[0.1, 0.2]]}')
    with patch(
        "backend.apps.matching.management.commands.index_retrieval.urlopen", return_value=response
    ) as urlopen:
        vectors = Command._embed("http://localhost:11434", "bge-m3", ["query text"])

    request = urlopen.call_args.args[0]
    assert request.full_url == "http://localhost:11434/api/embed"
    assert json.loads(request.data) == {"model": "bge-m3", "input": ["query text"]}
    assert vectors == [[0.1, 0.2]]


def test_dry_run_computes_vectors_without_storing_them() -> None:
    documents = {
        "offer": [EmbeddingDocument("offer", uuid4(), "Published offer")],
        "skill": [],
        "training": [],
    }
    command = Command()
    output = StringIO()

    with (
        patch.object(command, "stdout", output),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.indexable_documents",
            return_value=documents,
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.vector_extension_schema",
            return_value="extensions",
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.use_schema",
            return_value=nullcontext(),
        ),
        patch.object(Command, "_embed", return_value=[[0.0] * 1024]),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.store_embeddings"
        ) as store_embeddings,
    ):
        command.handle(
            model="bge-m3",
            base_url="http://localhost:11434",
            schema="eval_graphrag",
            limit=1,
            batch_size=1,
            dry_run=True,
        )

    store_embeddings.assert_not_called()
    assert "Would index 1 offer embeddings." in output.getvalue()


def test_rejects_vectors_with_unexpected_dimensions() -> None:
    documents = {
        "offer": [EmbeddingDocument("offer", uuid4(), "Published offer")],
        "skill": [],
        "training": [],
    }
    with (
        patch(
            "backend.apps.matching.management.commands.index_retrieval.indexable_documents",
            return_value=documents,
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.vector_extension_schema",
            return_value="extensions",
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.use_schema",
            return_value=nullcontext(),
        ),
        patch.object(Command, "_embed", return_value=[[0.0] * 3]),
        pytest.raises(CommandError, match="not sized to 1024"),
    ):
        Command().handle(
            model="bge-m3",
            base_url="http://localhost:11434",
            schema="eval_graphrag",
            limit=1,
            batch_size=1,
            dry_run=False,
        )
