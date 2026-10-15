from django.core.management import BaseCommand, CommandError
from django.db import connection
from psycopg import sql

from backend.apps.matching.services.evaluation_schema import EVALUATION_SCHEMA


class Command(BaseCommand):
    help = "Drop only the isolated eval_graphrag schema after explicit confirmation."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--confirm-schema", default="")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options) -> None:
        self.stdout.write(f"Target: schema {EVALUATION_SCHEMA} only; public will not be dropped.")
        if options["dry_run"]:
            self.stdout.write("No changes made.")
            return
        if options["confirm_schema"] != EVALUATION_SCHEMA:
            raise CommandError(f"Pass --confirm-schema {EVALUATION_SCHEMA} to drop it.")
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", [EVALUATION_SCHEMA])
            if cursor.fetchone() is None:
                self.stdout.write(f"Schema {EVALUATION_SCHEMA} does not exist.")
                return
            cursor.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(EVALUATION_SCHEMA))
            )
        self.stdout.write(self.style.SUCCESS(f"Dropped schema {EVALUATION_SCHEMA}."))
