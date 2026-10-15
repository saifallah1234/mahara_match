import ast
import json
import time
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from django.core.management import BaseCommand, CommandError, CommandParser
from django.db import InterfaceError, OperationalError, connection

from ai.llm.providers.embeddings import (
    EmbeddingConfig,
    EmbeddingDimensionError,
    EmbeddingUnavailable,
    embed,
    embedding_config,
)
from ai.retrieval.hybrid.retriever import ALL_LEGS, LEXICAL, VECTOR, retrieve
from backend.apps.matching.services.evaluation_retrieval import (
    RetrievalCase,
    candidate_details,
    relevance_metrics,
)
from backend.apps.matching.services.evaluation_schema import (
    EVALUATION_SCHEMA,
    use_schema,
    vector_extension_schema,
)
from backend.apps.matching.services.retrieval import catalogue_search

MODE_LEGS = {
    "baseline": frozenset({LEXICAL}),
    "hybrid": frozenset({LEXICAL, VECTOR}),
    "hybrid_graph": ALL_LEGS,
}


class Command(BaseCommand):
    help = "Produce retrieval candidates and optional judged metrics from eval_graphrag."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--schema", choices=(EVALUATION_SCHEMA,), required=True)
        parser.add_argument("--cases", type=Path, default=Path("retrieval_cases.py"))
        parser.add_argument(
            "--mode", choices=("baseline", "hybrid", "hybrid_graph"), default="baseline"
        )
        parser.add_argument("--model", help="Defaults to EMBEDDING_MODEL (bge-m3).")
        parser.add_argument("--base-url", help="Defaults to OLLAMA_BASE_URL.")
        parser.add_argument("--top-k", type=int, default=10)
        parser.add_argument("--batch-size", type=int, default=6)
        parser.add_argument("--retries", type=int, default=4)
        parser.add_argument("--retry-backoff", type=float, default=1.0)
        parser.add_argument("--output", type=Path, default=Path("retrieval_candidates.json"))

    def handle(self, *args: object, **options: Any) -> None:
        cases_path: Path = options["cases"]
        mode = str(options["mode"])
        top_k = options["top_k"]
        batch_size = options["batch_size"]
        retries = options["retries"]
        retry_backoff = options["retry_backoff"]
        if not isinstance(top_k, int) or top_k < 1:
            raise CommandError("--top-k must be a positive integer.")
        if not isinstance(batch_size, int) or batch_size < 1:
            raise CommandError("--batch-size must be a positive integer.")
        if not isinstance(retries, int) or retries < 1:
            raise CommandError("--retries must be a positive integer.")
        if not isinstance(retry_backoff, (float, int)) or retry_backoff < 0:
            raise CommandError("--retry-backoff must be a non-negative number.")
        cases = self._load_cases(cases_path)
        if len(cases) != 24:
            raise CommandError(f"Expected exactly 24 retrieval cases; found {len(cases)}.")

        config = embedding_config(options.get("model"), options.get("base_url"))
        model_name = config.model
        legs = MODE_LEGS[mode]
        question_vectors: dict[str, list[float]] = {}
        if VECTOR in legs:
            for start in range(0, len(cases), batch_size):
                batch_number = start // batch_size + 1
                batch = cases[start : start + batch_size]
                self.stdout.write(
                    f"Embedding questions {start + 1}-{start + len(batch)}/{len(cases)} "
                    f"(batch {batch_number})."
                )
                vectors = self._embed_questions(
                    config, [str(case["question"]) for case in batch], retries, float(retry_backoff)
                )
                question_vectors.update(
                    (case["id"], vector) for case, vector in zip(batch, vectors, strict=True)
                )

        extension_schema = self._database_with_retries(
            vector_extension_schema, "checking the pgvector extension", retries, retry_backoff
        )
        results = []
        with use_schema(EVALUATION_SCHEMA, extension_schema or EVALUATION_SCHEMA):
            searchable = self._database_with_retries(
                lambda: catalogue_search("", model_name).retrieval_documents,
                "loading evaluation documents",
                retries,
                retry_backoff,
            )
            for case_number, case in enumerate(cases, start=1):
                self.stdout.write(f"Retrieving case {case_number}/{len(cases)} ({case['id']}).")
                question = str(case["question"])
                vector = question_vectors.get(case["id"])
                ranking = self._database_with_retries(
                    lambda question=question, vector=vector: self._rank(
                        question, vector, model_name, legs, top_k, searchable
                    ),
                    f"retrieving case {case['id']}",
                    retries,
                    retry_backoff,
                )

                result: dict[str, object] = {
                    "case_id": case["id"],
                    "question": question,
                    "mode": mode,
                    "candidates": candidate_details(ranking, searchable, top_k),
                }
                if "relevant" in case:
                    result["metrics"] = relevance_metrics(
                        ranking, self._parse_relevant(case), top_k
                    )
                results.append(result)

        output_path: Path = options["output"]
        output_path.write_text(
            json.dumps(results, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        self.stdout.write(self.style.SUCCESS(f"Wrote {len(results)} cases to {output_path}."))

    @staticmethod
    def _rank(
        question: str,
        question_vector: list[float] | None,
        model_name: str,
        legs: frozenset[str],
        top_k: int,
        documents: list[Any],
    ) -> list[tuple[str, str]]:
        def precomputed(_: str) -> list[float]:
            if question_vector is None:
                raise CommandError("Question vector missing for a vector-leg mode.")
            return question_vector

        result = retrieve(
            question,
            catalogue_search(question, model_name, documents),
            legs=legs,
            vector_limit=top_k,
            embedder=precomputed,
        )
        return result.ranked

    @staticmethod
    def _embed_questions(
        config: EmbeddingConfig, questions: list[str], retries: int, retry_backoff: float
    ) -> list[list[float]]:
        try:
            return embed(
                questions,
                config,
                batch_size=len(questions),
                attempts=retries,
                backoff=retry_backoff,
            )
        except (EmbeddingUnavailable, EmbeddingDimensionError) as exc:
            raise CommandError(str(exc)) from exc

    def _database_with_retries(self, operation, label: str, retries: int, backoff: float):
        for attempt in range(1, retries + 1):
            try:
                return operation()
            except (InterfaceError, OperationalError) as exc:
                if not self._is_transient_database_error(str(exc)):
                    raise
                connection.close()
                if attempt == retries:
                    raise
                delay = backoff * (2 ** (attempt - 1))
                self.stderr.write(
                    f"Database connection interrupted while {label}; "
                    f"retry {attempt + 1}/{retries} in {delay:g}s."
                )
                time.sleep(delay)
        raise CommandError("Database retries exhausted.")

    @staticmethod
    def _is_transient_database_error(message: str) -> bool:
        message = message.casefold()
        return any(
            marker in message
            for marker in (
                "server closed the connection",
                "connection already closed",
                "connection is closed",
                "connection has been closed",
                "could not receive data from server",
                "could not send data to server",
                "ssl syscall error",
                "connection reset by peer",
                "connection timed out",
                "connection timeout expired",
                "connection failed",
                "connection refused",
                "could not connect",
                "network is unreachable",
                "no route to host",
                "broken pipe",
                "terminating connection due to administrator command",
            )
        )

    @staticmethod
    def _load_cases(path: Path) -> list[RetrievalCase]:
        if not path.is_file():
            raise CommandError(f"Retrieval case file not found: {path}")
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            cases_node = next(
                node.value
                for node in tree.body
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(target, ast.Name) and target.id == "CASES" for target in node.targets
                )
            )
            cases = ast.literal_eval(cases_node)
        except (SyntaxError, StopIteration, ValueError) as exc:
            raise CommandError("Expected a literal CASES = [...] in retrieval_cases.py.") from exc
        if not isinstance(cases, list) or len(cases) != 24:
            raise CommandError("Expected exactly 24 retrieval cases.")
        expected_fields = {"id", "language", "category", "question", "relevant"}
        seen_ids: set[str] = set()
        for case in cases:
            if not isinstance(case, dict) or set(case) != expected_fields:
                raise CommandError(
                    "Each case must contain exactly id, language, category, question, and relevant."
                )
            case_id = case["id"]
            if (
                not isinstance(case_id, str)
                or case_id in seen_ids
                or case["language"] not in {"fr", "ar"}
                or case["category"] not in {"keywords", "semantic", "multi_hop"}
                or not isinstance(case["question"], str)
                or not case["question"].strip()
            ):
                raise CommandError(
                    "Each case needs a unique ID, valid language/category, and question."
                )
            seen_ids.add(case_id)
            Command._parse_relevant(cast(RetrievalCase, case))

        cases_by_id = {case["id"]: case for case in cases}
        for case_id, case in cases_by_id.items():
            if case_id.startswith("fr_"):
                twin = cases_by_id.get("ar_" + case_id[3:])
                if twin is None or twin["relevant"] != case["relevant"]:
                    raise CommandError(f"French/Arabic relevance labels differ for {case_id}.")
        if (
            sum(case["language"] == "fr" for case in cases) != 12
            or sum(case["language"] == "ar" for case in cases) != 12
        ):
            raise CommandError("Expected 12 French and 12 Arabic retrieval cases.")
        return cases

    @staticmethod
    def _parse_relevant(case: RetrievalCase) -> list[tuple[str, str]]:
        labels = case.get("relevant", [])
        if not isinstance(labels, list):
            raise CommandError(f"Relevant labels for {case.get('id')} must be a literal list.")
        relevant: list[tuple[str, str]] = []
        for label in labels:
            if not isinstance(label, str):
                raise CommandError("Relevant labels must be strings like 'offer:<uuid>'.")
            entity_type, separator, raw_id = label.partition(":")
            if not separator or entity_type not in {"offer", "training"}:
                raise CommandError("Relevant labels use 'offer:<uuid>' or 'training:<uuid>'.")
            try:
                entity_id = UUID(raw_id)
            except ValueError as exc:
                raise CommandError(f"Invalid UUID in relevant label {label!r}.") from exc
            if raw_id != str(entity_id):
                raise CommandError(f"Relevant UUID must be canonical lowercase: {label!r}.")
            relevant.append((entity_type, str(entity_id)))
        canonical = [f"{entity_type}:{entity_id}" for entity_type, entity_id in relevant]
        if canonical != sorted(set(canonical)):
            raise CommandError(
                f"Relevant labels for {case.get('id')} must be duplicate-free and sorted."
            )
        return relevant
