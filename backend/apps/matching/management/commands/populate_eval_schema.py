from collections import Counter

from django.core.management import BaseCommand, CommandError
from django.db import transaction

from backend.apps.matching.services.evaluation_dataset import (
    PROGRAM_COUNT,
    SESSION_COUNT,
    clear_evaluation_data,
    plan_from_public_offers,
    populate_evaluation_schema,
)
from backend.apps.matching.services.evaluation_schema import EVALUATION_SCHEMA, use_schema


class Command(BaseCommand):
    help = "Prepare test-only retrieval data inside eval_graphrag; public is read-only."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--confirm", default="")
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Delete only TEST ONLY rows in eval_graphrag before repopulating.",
        )

    def handle(self, *args, **options) -> None:
        if not options["dry_run"] and options["confirm"] != EVALUATION_SCHEMA:
            raise CommandError(f"Pass --confirm {EVALUATION_SCHEMA} to write test data.")

        plan = plan_from_public_offers()
        statuses = Counter(str(offer["status"]) for offer in plan.offers)
        self.stdout.write(f"Read-only source: public.job_offers ({len(plan.offers)} rows).")
        self.stdout.write(f"Source statuses: {dict(sorted(statuses.items()))}.")
        self.stdout.write(f"Target: {EVALUATION_SCHEMA} only; no writes to public.")
        if options["replace"]:
            self.stdout.write(
                "Replace: TEST ONLY rows in eval_graphrag will be cleared before refill."
            )
        for skill_name in plan.skill_names:
            self.stdout.write(
                f"Skill: {skill_name} — {plan.skill_offer_counts[skill_name]} offers."
            )
        for program_number in range(PROGRAM_COUNT):
            skill_names = plan.program_skills[program_number]
            self.stdout.write(
                f"Program {program_number + 1}: TEST ONLY - Practical "
                f"{skill_names[0].title()} Program — skills: {', '.join(skill_names)}."
            )
        offer_skill_count = sum(len(names) for names in plan.offer_skills.values())
        training_skill_count = sum(len(names) for names in plan.program_skills.values())
        skills_without_training = len(plan.skill_names) - len(
            {name for names in plan.program_skills.values() for name in names}
        )
        total_rows = (
            len(plan.offers)
            + len(plan.skill_names)
            + offer_skill_count
            + 2
            + 1
            + 1
            + PROGRAM_COUNT
            + training_skill_count
            + SESSION_COUNT
        )
        self.stdout.write(
            "Planned TEST ONLY rows: "
            f"offers={len(plan.offers)}, skills={len(plan.skill_names)}, "
            f"offer_skills={offer_skill_count} (every selected skill mentioned per offer), "
            f"organizations=2, creator=1, source=1, programs={PROGRAM_COUNT}, "
            f"training_skills={training_skill_count}, "
            f"skills_without_training={skills_without_training}, sessions={SESSION_COUNT}; "
            f"total={total_rows}."
        )
        if options["dry_run"]:
            self.stdout.write("Dry run complete; nothing was written.")
            return

        with use_schema(EVALUATION_SCHEMA):
            cleared = None
            with transaction.atomic():
                if options["replace"]:
                    cleared = clear_evaluation_data()
                evaluation_counts = populate_evaluation_schema(plan)
            if cleared is not None:
                self.stdout.write(
                    "Cleared TEST ONLY rows: "
                    + ", ".join(f"{key}={value}" for key, value in cleared.items())
                    + "."
                )
        self.stdout.write(
            self.style.SUCCESS(
                "TEST ONLY data populated in eval_graphrag: "
                + ", ".join(f"{key}={value}" for key, value in evaluation_counts.items())
            )
        )
