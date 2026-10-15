import json
from collections.abc import Sequence
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError, CommandParser

from backend.apps.matching.services.embedding_index import (
    indexable_documents,
    store_embeddings,
)
from backend.apps.matching.services.evaluation_schema import (
    EVALUATION_SCHEMA,
    use_schema,
    vector_extension_schema,
)


class Command(BaseCommand):
    help = "Index published offers, canonical skills, and active training programs in pgvector."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--model", default="bge-m3")
        parser.add_argument("--base-url", default="http://localhost:11434")
        parser.add_argument("--schema", choices=(EVALUATION_SCHEMA,), default=EVALUATION_SCHEMA)
        parser.add_argument("--limit", type=int)
        parser.add_argument("--batch-size", type=int, default=16)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: object, **options: Any) -> None:
        limit = options["limit"]
        batch_size = options["batch_size"]
        if limit is not None and (not isinstance(limit, int) or limit < 1):
            raise CommandError("--limit must be a positive integer.")
        if not isinstance(batch_size, int) or batch_size < 1:
            raise CommandError("--batch-size must be a positive integer.")

        model_name = str(options["model"])
        base_url = str(options["base_url"]).rstrip("/")
        schema_name = str(options["schema"])
        dry_run = bool(options["dry_run"])
        with use_schema(schema_name, vector_extension_schema() or schema_name):
            documents = indexable_documents(limit=limit if isinstance(limit, int) else None)

            for entity_type, entity_documents in documents.items():
                indexed = 0
                for start in range(0, len(entity_documents), batch_size):
                    batch = entity_documents[start : start + batch_size]
                    vectors = self._embed(
                        base_url, model_name, [document.text for document in batch]
                    )
                    if any(len(vector) != 1024 for vector in vectors):
                        raise CommandError(
                            f"Ollama model {model_name!r} returned a vector not sized to 1024."
                        )
                    if not dry_run:
                        indexed += store_embeddings(batch, model_name, vectors)
                    else:
                        indexed += len(batch)
                action = "Would index" if dry_run else "Indexed"
                self.stdout.write(f"{action} {indexed} {entity_type} embeddings.")

    @staticmethod
    def _embed(base_url: str, model_name: str, inputs: Sequence[str]) -> list[list[float]]:
        request = Request(
            f"{base_url}/api/embed",
            data=json.dumps({"model": model_name, "input": inputs}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=120) as response:
                payload = json.load(response)
        except (HTTPError, URLError, TimeoutError) as exc:
            raise CommandError(f"Could not get embeddings from Ollama: {exc}") from exc
        vectors = payload.get("embeddings")
        if not isinstance(vectors, list) or len(vectors) != len(inputs):
            raise CommandError("Ollama returned an invalid embeddings response.")
        if any(not isinstance(vector, list) for vector in vectors):
            raise CommandError("Ollama returned a malformed vector.")
        return vectors
