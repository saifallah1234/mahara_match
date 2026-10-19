from pathlib import Path
from typing import Any

from django.core.management import BaseCommand, CommandError, CommandParser

from backend.apps.matching.management.commands.evaluate_retrieval import Command as EvaluateCommand
from backend.apps.matching.services.evaluation_label_audit import expected_relevant_labels
from backend.apps.matching.services.evaluation_schema import EVALUATION_SCHEMA, use_schema
from backend.apps.recruitment.models import JobOffer, OfferSkill
from backend.apps.training.models import TrainingProgram, TrainingSkill


class Command(BaseCommand):
    help = "Read-only validation of relevance labels against eval_graphrag skill links."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--schema", choices=(EVALUATION_SCHEMA,), required=True)
        parser.add_argument("--cases", type=Path, default=Path("retrieval_cases.py"))

    def handle(self, *args: object, **options: Any) -> None:
        cases = EvaluateCommand._load_cases(options["cases"])
        with use_schema(EVALUATION_SCHEMA):
            offer_skills: dict[str, set[str]] = {}
            for offer_id, skill_name in OfferSkill.objects.values_list(
                "offer_id", "skill__canonical_name"
            ):
                offer_skills.setdefault(str(offer_id), set()).add(skill_name)
            program_skills: dict[str, set[str]] = {}
            for program_id, skill_name in TrainingSkill.objects.values_list(
                "program_id", "skill__canonical_name"
            ):
                program_skills.setdefault(str(program_id), set()).add(skill_name)

            existing_offer_ids = {
                str(identifier) for identifier in JobOffer.objects.values_list("id", flat=True)
            }
            existing_program_ids = {
                str(identifier)
                for identifier in TrainingProgram.objects.values_list("id", flat=True)
            }

        failures = 0
        for case in cases:
            actual = case["relevant"]
            missing_ids = [
                label
                for label in actual
                if (
                    label.startswith("offer:")
                    and label.removeprefix("offer:") not in existing_offer_ids
                )
                or (
                    label.startswith("training:")
                    and label.removeprefix("training:") not in existing_program_ids
                )
            ]
            try:
                expected = expected_relevant_labels(case, offer_skills, program_skills)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            actual = sorted(actual)
            if missing_ids:
                failures += 1
                self.stdout.write(
                    self.style.ERROR(f"{case['id']}: NOT FOUND {', '.join(sorted(missing_ids))}")
                )
            elif actual == expected:
                self.stdout.write(self.style.SUCCESS(f"{case['id']}: OK ({len(actual)} labels)"))
            else:
                failures += 1
                missing = sorted(set(expected) - set(actual))
                extra = sorted(set(actual) - set(expected))
                self.stdout.write(self.style.ERROR(f"{case['id']}: DIFFERENCES"))
                self.stdout.write("  missing: " + (", ".join(missing) if missing else "none"))
                self.stdout.write("  extra: " + (", ".join(extra) if extra else "none"))

        self.stdout.write(f"Checked {len(cases)} cases; {failures} mismatched.")
        if failures:
            raise CommandError("Relevant-label validation failed.")
