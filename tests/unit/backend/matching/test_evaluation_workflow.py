from collections import Counter
from contextlib import nullcontext
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import URLError
from uuid import UUID

import pytest
from django.core.management.base import CommandError
from django.db import OperationalError

from backend.apps.matching.management.commands.cleanup_eval_schema import Command as CleanupCommand
from backend.apps.matching.management.commands.evaluate_retrieval import Command as EvaluateCommand
from backend.apps.matching.management.commands.index_retrieval import Command as IndexCommand
from backend.apps.matching.management.commands.populate_eval_schema import (
    Command as PopulateCommand,
)
from backend.apps.matching.services.embedding_index import EmbeddingDocument
from backend.apps.matching.services.evaluation_dataset import (
    _skill_mentions,
    build_program_skills,
    link_mentioned_skills,
)
from backend.apps.matching.services.evaluation_label_audit import expected_relevant_labels
from backend.apps.matching.services.evaluation_metrics import build_metric_report, metrics_for_case
from backend.apps.matching.services.evaluation_retrieval import RetrievalCase, relevance_metrics
from backend.apps.matching.services.evaluation_schema import EVALUATION_SCHEMA, schema_options
from backend.apps.matching.services.labeling_sheet import (
    Candidate,
    LabelingCase,
    render_labeling_sheet,
)

pytestmark = pytest.mark.unit


def test_schema_options_never_add_public_to_search_path() -> None:
    with patch(
        "backend.apps.matching.services.evaluation_schema.connection.settings_dict",
        {"OPTIONS": {"sslmode": "require"}},
    ):
        options = schema_options(EVALUATION_SCHEMA, "extensions")

    assert options == {"sslmode": "require", "options": "-c search_path=eval_graphrag,extensions"}
    with pytest.raises(ValueError, match="Invalid PostgreSQL schema"):
        schema_options("public;DROP SCHEMA public")


def test_cleanup_refuses_any_schema_other_than_eval_schema() -> None:
    command = CleanupCommand()
    with (
        patch(
            "backend.apps.matching.management.commands.cleanup_eval_schema.connection.cursor"
        ) as cursor,
        pytest.raises(CommandError, match="--confirm-schema eval_graphrag"),
    ):
        command.handle(confirm_schema="public", dry_run=False)
    cursor.assert_not_called()


def test_retrieval_cases_require_exactly_24_literal_questions() -> None:
    with TemporaryDirectory() as directory:
        cases_path = Path(directory) / "retrieval_cases.py"
        case_records = [
            {
                "id": f"{language}_keywords_{index:02}",
                "language": language,
                "category": "keywords",
                "question": f"question {index}",
                "relevant": [],
            }
            for index in range(1, 13)
            for language in ("fr", "ar")
        ]
        cases_path.write_text(f"CASES = {case_records!r}\n", encoding="utf-8")
        cases = EvaluateCommand._load_cases(cases_path)
    assert len(cases) == 24


def test_repository_relevance_labels_are_valid_sorted_and_symmetric() -> None:
    cases = EvaluateCommand._load_cases(Path("retrieval_cases.py"))
    by_id = {case["id"]: case for case in cases}

    assert len(by_id) == 24
    assert sum(case["language"] == "fr" for case in cases) == 12
    assert sum(case["language"] == "ar" for case in cases) == 12
    for case in cases:
        labels = case["relevant"]
        assert labels == sorted(set(labels))
        assert all(label.startswith(("offer:", "training:")) for label in labels)
        if case["language"] == "fr":
            assert by_id["ar_" + case["id"][3:]]["relevant"] == labels


def test_relevance_metrics_return_zero_for_explicit_no_relevant_items() -> None:
    assert relevance_metrics([("offer", "one")], [], limit=10) == {
        "mrr@10": 0.0,
        "recall@10": 0.0,
        "ndcg@10": 0.0,
    }


def test_absence_case_metrics_remove_training_labels_and_results() -> None:
    case: RetrievalCase = {
        "id": "fr_keywords_03",
        "language": "fr",
        "category": "keywords",
        "question": "PostgreSQL",
        "relevant": ["offer:one", "training:none"],
    }
    result = metrics_for_case(
        case,
        [("training", "none"), ("offer", "one")],
    )
    assert result["relevant_documents"] == 1
    assert result["training_candidates_excluded"] is True
    assert result["metrics"]["mrr"] == 1.0


def test_metric_report_builds_global_category_language_and_detail_records() -> None:
    cases: list[RetrievalCase] = [
        {
            "id": "fr_keywords_01",
            "language": "fr",
            "category": "keywords",
            "question": "Python",
            "relevant": ["offer:one"],
        }
    ]
    report = build_metric_report(
        cases,
        {
            "baseline": {"fr_keywords_01": [("offer", "one")]},
            "hybrid": {},
            "hybrid_graph": {},
        },
    )
    assert report["summaries"]["baseline"]["global"]["mrr"] == 1.0
    assert report["summaries"]["baseline"]["category"]["keywords"]["cases"] == 1
    assert report["summaries"]["baseline"]["language"]["fr"]["cases"] == 1
    assert report["per_case"][0]["relevant_documents"] == 1


def test_skill_extraction_canonicalizes_real_skills_and_ignores_generic_words() -> None:
    extracted = _skill_mentions(
        "Nous build solutions technical développement experience data données, "
        "Python, apprentissage automatique, machine learning, SQL, and sql."
    )
    assert extracted == {"Python": 1, "Machine Learning": 1, "SQL": 1}


def test_offer_skill_links_preserve_all_135_expected_mentions() -> None:
    expected_counts = {
        "Python": 23,
        "SQL": 16,
        "Artificial Intelligence": 15,
        "Git": 15,
        "CI/CD": 10,
        "Cloud Computing": 10,
        "Docker": 8,
        "Machine Learning": 7,
        "JavaScript": 6,
        "Data Engineering": 5,
        "Django": 5,
        "Azure": 4,
        "Java": 4,
        "PostgreSQL": 4,
        "Apache Spark": 3,
    }
    offer_ids = [UUID(int=index + 1) for index in range(23)]
    mentions: dict[UUID, Counter[str]] = {offer_id: Counter() for offer_id in offer_ids}
    for skill_name, count in expected_counts.items():
        for offer_id in offer_ids[:count]:
            mentions[offer_id][skill_name] = 1

    linked = link_mentioned_skills(mentions, tuple(expected_counts))
    actual_counts = Counter(skill for skills in linked.values() for skill in skills)

    assert actual_counts == expected_counts
    assert sum(map(len, linked.values())) == 135
    assert set(linked[offer_ids[0]]) == set(expected_counts)


def test_relevance_audit_rules_recompute_keyword_and_multihop_sets() -> None:
    offer_skills = {
        "offer-python-sql": {"Python", "SQL", "Docker"},
        "offer-docker": {"Docker", "Machine Learning"},
        "offer-spark": {"Apache Spark", "Python"},
    }
    program_skills = {
        "program-python": {"Python", "SQL"},
        "program-docker": {"Docker"},
        "program-spark": {"Apache Spark"},
    }
    assert expected_relevant_labels({"id": "fr_keywords_01"}, offer_skills, program_skills) == [
        "offer:offer-python-sql",
        "training:program-python",
    ]
    assert expected_relevant_labels({"id": "fr_multi_hop_02"}, offer_skills, program_skills) == [
        "offer:offer-docker",
        "offer:offer-python-sql",
        "training:program-docker",
        "training:program-python",
    ]
    assert expected_relevant_labels({"id": "fr_multi_hop_03"}, offer_skills, program_skills) == [
        "offer:offer-spark"
    ]


@pytest.mark.parametrize(("count", "untrained"), [(12, 2), (13, 2), (14, 2), (15, 3)])
def test_program_skills_leave_two_or_three_skills_uncovered(count: int, untrained: int) -> None:
    skill_names = tuple(f"Skill {index}" for index in range(count))
    programs = build_program_skills(skill_names)

    assert len(programs) == 6
    assert all(2 <= len(skills) <= 4 for skills in programs.values())
    trained = {skill for skills in programs.values() for skill in skills}
    assert len(set(skill_names) - trained) == untrained


def test_database_retry_recovers_from_a_transient_connection_cut() -> None:
    command = EvaluateCommand()
    operation = patch(
        "backend.apps.matching.management.commands.evaluate_retrieval.connection.close"
    )
    attempts = 0

    def read_once() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise OperationalError("server closed the connection unexpectedly")
        return "ok"

    with (
        operation as close_connection,
        patch("backend.apps.matching.management.commands.evaluate_retrieval.time.sleep"),
    ):
        assert command._database_with_retries(read_once, "reading", 3, 0) == "ok"

    assert attempts == 2
    close_connection.assert_called_once()


def test_database_retry_does_not_hide_permanent_sql_errors() -> None:
    command = EvaluateCommand()
    attempts = 0

    def read_once() -> None:
        nonlocal attempts
        attempts += 1
        raise OperationalError('relation "missing_table" does not exist')

    with (
        pytest.raises(OperationalError, match="does not exist"),
        patch("backend.apps.matching.management.commands.evaluate_retrieval.time.sleep") as sleep,
    ):
        command._database_with_retries(read_once, "reading", 4, 0)

    assert attempts == 1
    sleep.assert_not_called()


def test_ollama_retry_recovers_from_a_transient_network_failure() -> None:
    command = EvaluateCommand()
    attempts = 0

    def embed(*args: object) -> list[list[float]]:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise CommandError("temporary network error") from URLError("connection reset")
        return [[0.0] * 1024]

    with (
        patch.object(IndexCommand, "_embed", side_effect=embed),
        patch("backend.apps.matching.management.commands.evaluate_retrieval.time.sleep"),
    ):
        vectors = command._embed_with_retries(
            "http://localhost:11434", "bge-m3", ["question"], 1, 3, 0
        )

    assert attempts == 2
    assert vectors == [[0.0] * 1024]


def test_hybrid_embeddings_are_computed_before_database_access() -> None:
    with TemporaryDirectory() as directory:
        cases_path = Path(directory) / "retrieval_cases.py"
        cases = [
            {
                "id": f"{language}_keywords_{index:02}",
                "language": language,
                "category": "keywords",
                "question": f"question {index}",
                "relevant": [],
            }
            for index in range(1, 13)
            for language in ("fr", "ar")
        ]
        cases_path.write_text(f"CASES = {cases!r}\n", encoding="utf-8")
        command = EvaluateCommand()
        database_started = False
        batches = 0

        def embed_batch(*args: object) -> list[list[float]]:
            nonlocal batches
            assert not database_started
            batches += 1
            return [[0.0] * 1024 for _ in range(6)]

        def mark_database_started() -> None:
            nonlocal database_started
            assert batches == 4
            database_started = True

        with (
            patch.object(command, "stdout", StringIO()),
            patch.object(command, "stderr", StringIO()),
            patch.object(command, "_embed_with_retries", side_effect=embed_batch),
            patch.object(command, "_database_with_retries", side_effect=lambda fn, *args: fn()),
            patch(
                "backend.apps.matching.management.commands.evaluate_retrieval.vector_extension_schema",
                side_effect=mark_database_started,
            ),
            patch(
                "backend.apps.matching.management.commands.evaluate_retrieval.use_schema",
                return_value=nullcontext(),
            ),
            patch(
                "backend.apps.matching.management.commands.evaluate_retrieval.indexable_documents",
                return_value={
                    "offer": [EmbeddingDocument("offer", UUID(int=1), "Python")],
                    "skill": [],
                    "training": [],
                },
            ),
            patch(
                "backend.apps.matching.management.commands.evaluate_retrieval.semantic_ranking",
                return_value=[("offer", str(UUID(int=1)))],
            ),
            patch("backend.apps.matching.management.commands.evaluate_retrieval.Path.write_text"),
        ):
            command.handle(
                schema="eval_graphrag",
                cases=cases_path,
                mode="hybrid",
                model="bge-m3",
                base_url="http://localhost:11434",
                top_k=10,
                batch_size=6,
                retries=2,
                retry_backoff=0,
                output=Path(directory) / "result.json",
            )

        assert database_started


def test_labeling_sheet_deduplicates_sorts_and_hides_retrieval_provenance() -> None:
    case: LabelingCase = {
        "id": "fr_keywords_01",
        "language": "fr",
        "category": "keywords",
        "question": "Python et SQL",
    }
    first_id = "00000000-0000-0000-0000-000000000001"
    second_id = "00000000-0000-0000-0000-000000000002"
    candidates: dict[str, list[Candidate]] = {
        "fr_keywords_01": [
            {"type": "offer", "id": first_id, "title": "Source order title"},
            {"type": "offer", "id": second_id, "title": "Another title"},
            {"type": "offer", "id": first_id, "title": "Duplicate from another mode"},
        ]
    }
    catalog = {
        ("offer", first_id): ("Zulu offer", ("Python",)),
        ("offer", second_id): ("Alpha offer", ("SQL",)),
    }

    sheet = render_labeling_sheet([case], candidates, catalog)

    assert sheet.count(f"offer:{first_id}") == 1
    assert sheet.index("Alpha offer") < sheet.index("Zulu offer")
    assert "Suggestion à valider : l’offre est liée aux compétences citées : SQL." in sheet
    assert "baseline" not in sheet and "hybrid" not in sheet and "rank" not in sheet


def test_replace_dry_run_never_clears_or_populates() -> None:
    plan = _tiny_plan()
    command = PopulateCommand()
    with (
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.plan_from_public_offers",
            return_value=plan,
        ),
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.clear_evaluation_data"
        ) as clear,
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.populate_evaluation_schema"
        ) as populate,
    ):
        command.handle(dry_run=True, confirm="", replace=True)

    clear.assert_not_called()
    populate.assert_not_called()


def test_replace_confirmation_clears_and_repopulates_only_inside_eval_context() -> None:
    plan = _tiny_plan()
    command = PopulateCommand()
    with (
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.plan_from_public_offers",
            return_value=plan,
        ),
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.use_schema",
            return_value=nullcontext(),
        ) as use_schema,
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.transaction.atomic",
            return_value=nullcontext(),
        ),
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.clear_evaluation_data",
            return_value={"offers": 23, "embeddings": 10},
        ) as clear,
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.populate_evaluation_schema",
            return_value={"offers": 23},
        ) as populate,
    ):
        command.handle(dry_run=False, confirm="eval_graphrag", replace=True)

    use_schema.assert_called_once_with("eval_graphrag")
    clear.assert_called_once_with()
    populate.assert_called_once_with(plan)


def test_replace_plan_then_nested_eval_write_keeps_transaction_connection_open() -> None:
    from backend.apps.matching.services import evaluation_schema

    class ConnectionHarness:
        settings_dict = {"OPTIONS": {"sslmode": "require"}}
        in_atomic_block = False
        is_closed = True
        closed_during_atomic = False

        def close(self) -> None:
            self.is_closed = True
            self.closed_during_atomic |= self.in_atomic_block

    connection = ConnectionHarness()
    plan = _tiny_plan()

    class AtomicHarness:
        def __enter__(self) -> None:
            connection.in_atomic_block = True
            connection.is_closed = False

        def __exit__(self, *_args: object) -> None:
            connection.in_atomic_block = False

    def read_plan() -> SimpleNamespace:
        with evaluation_schema.use_schema("public"):
            assert connection.settings_dict["OPTIONS"]["options"] == "-c search_path=public"
        return plan

    def write_plan(_plan: SimpleNamespace) -> dict[str, int]:
        with evaluation_schema.use_schema("eval_graphrag"):
            if connection.is_closed:
                raise OperationalError("the connection is closed")
            assert connection.settings_dict["OPTIONS"]["options"] == (
                "-c search_path=eval_graphrag"
            )
        return {"offers": 23}

    command = PopulateCommand()
    with (
        patch.object(evaluation_schema, "connection", connection),
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.plan_from_public_offers",
            side_effect=read_plan,
        ),
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.clear_evaluation_data"
        ),
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.populate_evaluation_schema",
            side_effect=write_plan,
        ),
        patch(
            "backend.apps.matching.management.commands.populate_eval_schema.transaction.atomic",
            return_value=AtomicHarness(),
        ),
    ):
        command.handle(dry_run=False, confirm="eval_graphrag", replace=True)

    assert not connection.closed_during_atomic


def _tiny_plan() -> SimpleNamespace:
    skill_names = tuple(f"Skill {index}" for index in range(12))
    return SimpleNamespace(
        offers=tuple({"status": "DRAFT"} for _ in range(22)) + ({"status": "PUBLISHED"},),
        skill_names=skill_names,
        skill_offer_counts={skill_name: 23 for skill_name in skill_names},
        offer_skills={UUID(int=index + 1): skill_names[:2] for index in range(23)},
        program_skills={index: skill_names[:2] for index in range(6)},
    )
