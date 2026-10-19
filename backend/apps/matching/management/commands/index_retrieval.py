from argparse import BooleanOptionalAction
from contextlib import AbstractContextManager, nullcontext
from typing import Any

from django.core.management.base import BaseCommand, CommandError, CommandParser

from ai.llm.providers.embeddings import (
    EmbeddingConfig,
    EmbeddingDimensionError,
    EmbeddingUnavailable,
    embed,
    embedding_config,
)
from backend.apps.matching.services.embedding_index import (
    delete_stale_embeddings,
    indexable_documents,
    stale_embeddings,
    store_embeddings,
)
from backend.apps.matching.services.evaluation_schema import (
    EVALUATION_SCHEMA,
    use_schema,
    vector_extension_schema,
)
from backend.common.retrieval import RetrievalDocument

PUBLIC_SCHEMA = "public"


class Command(BaseCommand):
    help = (
        "Index offers, canonical skills, active training programs and opted-in limited "
        "candidate profiles in pgvector, and prune vectors that are no longer indexable."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--model", help="Defaults to EMBEDDING_MODEL (bge-m3).")
        parser.add_argument("--base-url", help="Defaults to OLLAMA_BASE_URL.")
        parser.add_argument(
            "--schema",
            choices=(EVALUATION_SCHEMA, PUBLIC_SCHEMA),
            default=EVALUATION_SCHEMA,
            help="public is the application schema read at runtime; eval_graphrag is isolated.",
        )
        parser.add_argument("--limit", type=int)
        parser.add_argument("--batch-size", type=int, default=16)
        parser.add_argument(
            "--prune",
            action=BooleanOptionalAction,
            default=None,
            help="Delete this model's vectors for entities no longer indexable. "
            "Defaults to on for public, off for eval_graphrag.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute vectors and list upserts and deletions without writing.",
        )

    def handle(self, *args: object, **options: Any) -> None:
        limit = options["limit"]
        batch_size = options["batch_size"]
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise CommandError("--limit must be a positive integer.")
        if not isinstance(batch_size, int) or batch_size < 1:
            raise CommandError("--batch-size must be a positive integer.")

        config = embedding_config(options.get("model"), options.get("base_url"))
        schema_name = str(options["schema"])
        dry_run = bool(options["dry_run"])
        prune = options.get("prune")
        if prune is None:
            prune = schema_name == PUBLIC_SCHEMA
        if prune and limit is not None:
            raise CommandError(
                "--prune needs the full document set; drop --limit or use --no-prune."
            )

        context: AbstractContextManager[None] = (
            nullcontext()
            if schema_name == PUBLIC_SCHEMA
            else use_schema(schema_name, vector_extension_schema() or schema_name)
        )
        with context:
            documents = indexable_documents(limit=limit if isinstance(limit, int) else None)
            self._index(documents, config, batch_size, dry_run)
            if prune:
                self._prune(documents, config.model, dry_run)

    def _index(
        self,
        documents: dict[str, list[RetrievalDocument]],
        config: EmbeddingConfig,
        batch_size: int,
        dry_run: bool,
    ) -> None:
        for entity_type, entity_documents in documents.items():
            indexed = 0
            for start in range(0, len(entity_documents), batch_size):
                batch = entity_documents[start : start + batch_size]
                try:
                    vectors = embed(
                        [document.text for document in batch], config, batch_size=batch_size
                    )
                except (EmbeddingUnavailable, EmbeddingDimensionError) as exc:
                    raise CommandError(str(exc)) from exc
                if not dry_run:
                    indexed += store_embeddings(batch, config.model, vectors)
                else:
                    indexed += len(batch)
            action = "Would index" if dry_run else "Indexed"
            self.stdout.write(f"{action} {indexed} {entity_type} embeddings.")

    def _prune(
        self, documents: dict[str, list[RetrievalDocument]], model_name: str, dry_run: bool
    ) -> None:
        keep = {
            entity_type: {document.entity_id for document in entity_documents}
            for entity_type, entity_documents in documents.items()
        }
        if dry_run:
            stale = list(stale_embeddings(model_name, keep).values_list("entity_type", "entity_id"))
            self.stdout.write(f"Would delete {len(stale)} stale {model_name} embeddings.")
            for entity_type, entity_id in stale:
                self.stdout.write(f"  - {entity_type} {entity_id}")
            return
        deleted = delete_stale_embeddings(model_name, keep)
        self.stdout.write(f"Deleted {deleted} stale {model_name} embeddings.")
