from django.core.management import BaseCommand, CommandError, call_command
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.recorder import MigrationRecorder
from psycopg import sql

from backend.apps.matching.services.evaluation_schema import (
    EVALUATION_SCHEMA,
    use_schema,
    vector_extension_schema,
)


class Command(BaseCommand):
    help = "Create the persistent eval_graphrag schema and apply Django migrations there."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--confirm", default="")

    def handle(self, *args, **options) -> None:
        if not options["dry_run"] and options["confirm"] != EVALUATION_SCHEMA:
            raise CommandError(f"Pass --confirm {EVALUATION_SCHEMA} to create or migrate it.")

        loader = MigrationLoader(None, ignore_no_migrations=True)
        targets = sorted(f"{app}.{name}" for app, name in loader.graph.leaf_nodes())
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_namespace WHERE nspname = %s", [EVALUATION_SCHEMA])
            exists = cursor.fetchone() is not None

        action = "reuse and migrate" if exists else "create and migrate"
        self.stdout.write(f"Would {action} schema {EVALUATION_SCHEMA}.")
        self.stdout.write("Migration targets: " + ", ".join(targets))
        if options["dry_run"]:
            return

        if not exists:
            with connection.cursor() as cursor:
                cursor.execute(
                    sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(EVALUATION_SCHEMA))
                )
                cursor.execute(
                    sql.SQL("COMMENT ON SCHEMA {} IS %s").format(sql.Identifier(EVALUATION_SCHEMA)),
                    ["TEST DATA ONLY: isolated GraphRAG evaluation schema"],
                )

        extension_schema = vector_extension_schema()
        with use_schema(EVALUATION_SCHEMA):
            MigrationRecorder(connection).ensure_schema()
        with use_schema(EVALUATION_SCHEMA, extension_schema or EVALUATION_SCHEMA):
            call_command("migrate", interactive=False, verbosity=1)
        self.stdout.write(self.style.SUCCESS(f"Schema {EVALUATION_SCHEMA} is ready."))
