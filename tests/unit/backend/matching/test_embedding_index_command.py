from contextlib import nullcontext
from io import StringIO
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from django.core.management.base import CommandError

from ai.llm.providers.embeddings import EmbeddingDimensionError
from backend.apps.matching.management.commands.index_retrieval import Command
from backend.common.retrieval import RetrievalDocument

pytestmark = pytest.mark.unit


def test_dry_run_computes_vectors_without_storing_them() -> None:
    documents = {
        "offer": [RetrievalDocument("offer", uuid4(), "Published offer")],
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
        patch(
            "backend.apps.matching.management.commands.index_retrieval.embed",
            return_value=[[0.0] * 1024],
        ) as embed,
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
    assert embed.call_args.args[1].model == "bge-m3"
    assert "Would index 1 offer embeddings." in output.getvalue()


def test_dimension_mismatch_is_a_command_error() -> None:
    documents = {
        "offer": [RetrievalDocument("offer", uuid4(), "Published offer")],
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
        patch(
            "backend.apps.matching.management.commands.index_retrieval.embed",
            side_effect=EmbeddingDimensionError("returned 3-dimension vectors"),
        ),
        pytest.raises(CommandError, match="3-dimension"),
    ):
        Command().handle(
            model="bge-m3",
            base_url="http://localhost:11434",
            schema="eval_graphrag",
            limit=1,
            batch_size=1,
            dry_run=False,
        )


def _patched_documents(documents: dict[str, list[RetrievalDocument]]) -> Any:
    return patch(
        "backend.apps.matching.management.commands.index_retrieval.indexable_documents",
        return_value=documents,
    )


def _options(**overrides: Any) -> dict[str, Any]:
    return {
        "model": "bge-m3",
        "base_url": "http://localhost:11434",
        "schema": "public",
        "limit": None,
        "batch_size": 16,
        "prune": None,
        "dry_run": True,
        **overrides,
    }


def test_public_dry_run_lists_deletions_without_switching_schema() -> None:
    kept = uuid4()
    stale_id = uuid4()
    documents = {"offer": [RetrievalDocument("offer", kept, "Offer")]}
    command = Command()
    output = StringIO()
    stale = MagicMock()
    stale.values_list.return_value = [("offer", stale_id)]

    with (
        patch.object(command, "stdout", output),
        _patched_documents(documents),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.use_schema",
            side_effect=AssertionError("public uses the default connection"),
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.embed",
            return_value=[[0.0] * 1024],
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.stale_embeddings",
            return_value=stale,
        ) as stale_embeddings,
        patch(
            "backend.apps.matching.management.commands.index_retrieval.delete_stale_embeddings"
        ) as delete,
        patch(
            "backend.apps.matching.management.commands.index_retrieval.store_embeddings"
        ) as store,
    ):
        command.handle(**_options())

    assert stale_embeddings.call_args.args == ("bge-m3", {"offer": {kept}})
    delete.assert_not_called()
    store.assert_not_called()
    assert "Would delete 1 stale bge-m3 embeddings." in output.getvalue()
    assert f"  - offer {stale_id}" in output.getvalue()


def test_prune_is_off_by_default_for_the_evaluation_schema() -> None:
    with (
        _patched_documents({"offer": []}),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.vector_extension_schema",
            return_value="extensions",
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.use_schema",
            return_value=nullcontext(),
        ),
        patch(
            "backend.apps.matching.management.commands.index_retrieval.stale_embeddings"
        ) as stale_embeddings,
    ):
        Command().handle(**_options(schema="eval_graphrag"))

    stale_embeddings.assert_not_called()


def test_prune_refuses_a_partial_document_set() -> None:
    with pytest.raises(CommandError, match="--prune needs the full document set"):
        Command().handle(**_options(limit=5))
