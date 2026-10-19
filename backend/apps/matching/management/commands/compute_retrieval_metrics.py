import json
from pathlib import Path
from typing import Any

from django.core.management import BaseCommand, CommandError, CommandParser

from backend.apps.matching.management.commands.evaluate_retrieval import Command as EvaluateCommand
from backend.apps.matching.services.evaluation_metrics import build_metric_report
from backend.apps.matching.services.evaluation_retrieval import RetrievalCase


class Command(BaseCommand):
    help = "Compute retrieval metrics from local candidate JSON files; does not access a database."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--cases", type=Path, default=Path("retrieval_cases.py"))
        parser.add_argument("--baseline", type=Path, default=Path("candidates-baseline.json"))
        parser.add_argument("--hybrid", type=Path, default=Path("candidates-hybrid.json"))
        parser.add_argument(
            "--hybrid-graph", type=Path, default=Path("candidates-hybrid-graph.json")
        )
        parser.add_argument("--output", type=Path, default=Path("metrics-retrieval.json"))

    def handle(self, *args: object, **options: Any) -> None:
        cases = EvaluateCommand._load_cases(options["cases"])
        if len(cases) != 24:
            raise CommandError(f"Expected exactly 24 cases; found {len(cases)}.")

        rankings_by_mode = {
            mode: self._read_rankings(Path(options[option_name]), cases)
            for mode, option_name in (
                ("baseline", "baseline"),
                ("hybrid", "hybrid"),
                ("hybrid_graph", "hybrid_graph"),
            )
        }
        report = build_metric_report(cases, rankings_by_mode)
        self._write_markdown_tables(report["summaries"])
        output: Path = options["output"]
        output.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        self.stdout.write(self.style.SUCCESS(f"Wrote per-case metrics to {output} (UTF-8)."))

    @staticmethod
    def _read_rankings(path: Path, cases: list[RetrievalCase]) -> dict[str, list[tuple[str, str]]]:
        if not path.is_file():
            raise CommandError(f"Candidate file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read {path}: {exc}") from exc
        if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
            raise CommandError(f"{path} must contain a JSON array of case results.")
        expected_ids = {case["id"] for case in cases}
        result_ids = [item.get("case_id") for item in data]
        if len(result_ids) != 24 or set(result_ids) != expected_ids:
            raise CommandError(f"{path} must contain exactly the 24 retrieval case IDs.")

        rankings: dict[str, list[tuple[str, str]]] = {}
        for item in data:
            case_id = item["case_id"]
            candidates = item.get("candidates")
            if not isinstance(candidates, list):
                raise CommandError(f"Candidates are missing for {case_id} in {path}.")
            ranking = []
            for candidate in candidates:
                if (
                    not isinstance(candidate, dict)
                    or candidate.get("type") not in {"offer", "training"}
                    or not isinstance(candidate.get("id"), str)
                ):
                    raise CommandError(f"Invalid candidate for {case_id} in {path}.")
                ranking.append((candidate["type"], candidate["id"]))
            rankings[case_id] = ranking
        return rankings

    def _write_markdown_tables(self, summaries: dict[str, Any]) -> None:
        header = (
            "| Groupe | Cas | Documents pertinents/cas | MRR | Recall@5 | Recall@10 | NDCG@3 | NDCG@5 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        )
        for mode, groups in summaries.items():
            self.stdout.write(f"\n### {mode}")
            self.stdout.write("\n".join(header))
            self._write_group_row("global", "tous", groups["global"])
            for category, metrics in groups["category"].items():
                self._write_group_row("catégorie", category, metrics)
            for language, metrics in groups["language"].items():
                self._write_group_row("langue", language, metrics)

    def _write_group_row(self, dimension: str, group: str, metrics: dict[str, float | int]) -> None:
        self.stdout.write(
            "| "
            + " | ".join(
                (
                    f"{dimension}: {group}",
                    str(metrics["cases"]),
                    f"{metrics['relevant_documents_per_case']:.2f}",
                    f"{metrics['mrr']:.4f}",
                    f"{metrics['recall@5']:.4f}",
                    f"{metrics['recall@10']:.4f}",
                    f"{metrics['ndcg@3']:.4f}",
                    f"{metrics['ndcg@5']:.4f}",
                )
            )
            + " |"
        )
