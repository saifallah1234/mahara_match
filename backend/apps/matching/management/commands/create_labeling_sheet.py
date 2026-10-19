import json
from pathlib import Path
from typing import Any
from uuid import UUID

from django.core.management import BaseCommand, CommandError, CommandParser

from backend.apps.matching.management.commands.evaluate_retrieval import Command as EvaluateCommand
from backend.apps.matching.services.evaluation_schema import EVALUATION_SCHEMA, use_schema
from backend.apps.matching.services.labeling_sheet import (
    Candidate,
    LabelingCase,
    render_labeling_sheet,
)
from backend.apps.recruitment.models import JobOffer, OfferSkill
from backend.apps.training.models import TrainingProgram, TrainingSkill


class Command(BaseCommand):
    help = "Create a neutral UTF-8 labeling sheet from existing candidate outputs."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--cases", type=Path, default=Path("retrieval_cases.py"))
        parser.add_argument("--baseline", type=Path, default=Path("candidates-baseline.json"))
        parser.add_argument("--hybrid", type=Path, default=Path("candidates-hybrid.json"))
        parser.add_argument(
            "--hybrid-graph", type=Path, default=Path("candidates-hybrid-graph.json")
        )
        parser.add_argument("--output", type=Path, default=Path("labeling_sheet.md"))

    def handle(self, *args: object, **options: Any) -> None:
        cases_path: Path = options["cases"]
        try:
            parsed_cases = EvaluateCommand._load_cases(cases_path)
        except CommandError as exc:
            raise CommandError(str(exc)) from exc
        if len(parsed_cases) != 24:
            raise CommandError(
                f"Expected exactly 24 cases in {cases_path}; found {len(parsed_cases)}."
            )
        if any(
            case.get("language") not in {"fr", "ar"}
            or case.get("category") not in {"keywords", "semantic", "multi_hop"}
            for case in parsed_cases
        ):
            raise CommandError("Each retrieval case needs language fr/ar and a supported category.")
        cases: list[LabelingCase] = [
            {
                "id": case["id"],
                "language": case["language"],
                "category": case["category"],
                "question": case["question"],
            }
            for case in parsed_cases
        ]

        candidates_by_case: dict[str, dict[tuple[str, str], Candidate]] = {
            case["id"]: {} for case in cases
        }
        for option_name in ("baseline", "hybrid", "hybrid_graph"):
            path: Path = options[option_name]
            candidate_cases = self._read_candidate_file(path)
            candidate_case_ids = [
                candidate_case.get("case_id") for candidate_case in candidate_cases
            ]
            if len(candidate_case_ids) != 24 or set(candidate_case_ids) != set(candidates_by_case):
                raise CommandError(f"{path} must contain exactly the 24 retrieval case IDs.")
            for candidate_case in candidate_cases:
                case_id = candidate_case.get("case_id")
                if case_id not in candidates_by_case:
                    raise CommandError(f"Unknown case_id {case_id!r} in {path}.")
                for candidate in candidate_case.get("candidates", []):
                    if (
                        not isinstance(candidate, dict)
                        or candidate.get("type") not in {"offer", "training"}
                        or not isinstance(candidate.get("id"), str)
                        or not isinstance(candidate.get("title"), str)
                    ):
                        raise CommandError(f"Malformed candidate in {path}, case {case_id}.")
                    key = (candidate["type"], candidate["id"])
                    candidates_by_case[case_id].setdefault(
                        key,
                        {
                            "type": candidate["type"],
                            "id": candidate["id"],
                            "title": candidate["title"],
                        },
                    )

        all_candidates = {
            key for case_candidates in candidates_by_case.values() for key in case_candidates
        }
        catalog = self._load_catalog(all_candidates)
        sheet = render_labeling_sheet(
            cases,
            {
                case_id: tuple(candidates.values())
                for case_id, candidates in candidates_by_case.items()
            },
            catalog,
        )
        output: Path = options["output"]
        output.write_text(sheet, encoding="utf-8", newline="\n")
        self.stdout.write(
            self.style.SUCCESS(
                f"Wrote {len(cases)} cases and {len(all_candidates)} unique candidates "
                f"to {output} (UTF-8). No database data was changed."
            )
        )

    @staticmethod
    def _read_candidate_file(path: Path) -> list[dict[str, Any]]:
        if not path.is_file():
            raise CommandError(f"Candidate file not found: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CommandError(f"Could not read candidate JSON {path}: {exc}") from exc
        if not isinstance(data, list) or any(not isinstance(case, dict) for case in data):
            raise CommandError(f"Candidate file {path} must contain a JSON array of cases.")
        return data

    @staticmethod
    def _load_catalog(
        candidates: set[tuple[str, str]],
    ) -> dict[tuple[str, str], tuple[str, tuple[str, ...]]]:
        offer_ids = [UUID(identifier) for kind, identifier in candidates if kind == "offer"]
        training_ids = [UUID(identifier) for kind, identifier in candidates if kind == "training"]
        catalog: dict[tuple[str, str], tuple[str, tuple[str, ...]]] = {}
        with use_schema(EVALUATION_SCHEMA):
            for offer in JobOffer.objects.filter(id__in=offer_ids).values("id", "title"):
                key = ("offer", str(offer["id"]))
                catalog[key] = (offer["title"], ())
            for offer_id, skill_name in OfferSkill.objects.filter(
                offer_id__in=offer_ids
            ).values_list("offer_id", "skill__canonical_name"):
                key = ("offer", str(offer_id))
                if key in catalog:
                    title, skills = catalog[key]
                    catalog[key] = (title, tuple(sorted({*skills, skill_name}, key=str.casefold)))

            for program in TrainingProgram.objects.filter(id__in=training_ids).values(
                "id", "title"
            ):
                key = ("training", str(program["id"]))
                catalog[key] = (program["title"], ())
            for program_id, skill_name in TrainingSkill.objects.filter(
                program_id__in=training_ids
            ).values_list("program_id", "skill__canonical_name"):
                key = ("training", str(program_id))
                if key in catalog:
                    title, skills = catalog[key]
                    catalog[key] = (title, tuple(sorted({*skills, skill_name}, key=str.casefold)))

        missing = candidates - set(catalog)
        if missing:
            formatted = ", ".join(f"{kind}:{identifier}" for kind, identifier in sorted(missing))
            raise CommandError(
                "Some candidate IDs are not present in eval_graphrag; no sheet was written: "
                + formatted
            )
        return catalog
