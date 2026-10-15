"""Session-wide test database setup shared by unit, integration and e2e tests.

One definition for the whole suite: a per-directory override would make e2e tests
create the test database a second time while integration tests still hold it.
"""

import os
from collections.abc import Generator
from typing import Any
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder
from django.test.utils import setup_databases, teardown_databases
from psycopg import sql

DATABASE_URL_VARIABLES = ("TEST_DATABASE_URL", "DATABASE_URL", "POSTGRES_SESSION_POOLER")


@pytest.fixture(scope="session")
def django_db_setup(
    request: pytest.FixtureRequest,
    django_db_blocker: Any,
    django_db_keepdb: bool,
    django_db_createdb: bool,
    django_db_modify_db_settings: None,
) -> Generator[None]:
    # Settings that name a dedicated test database (interview_test points at a local,
    # disposable server) keep Django's normal test-database creation.
    if connection.settings_dict.get("TEST", {}).get("NAME"):
        with django_db_blocker.unblock():
            database_config = setup_databases(
                verbosity=request.config.option.verbose,
                interactive=False,
                keepdb=django_db_keepdb and not django_db_createdb,
            )
        yield
        if not django_db_keepdb:
            with django_db_blocker.unblock():
                teardown_databases(database_config, verbosity=request.config.option.verbose)
        return

    # Otherwise never fall back to Django's CREATE DATABASE test_<name>: on the shared
    # server it leaves a stray database behind whenever a run is interrupted.
    database_url = next(filter(None, map(os.getenv, DATABASE_URL_VARIABLES)), None)
    if not database_url:
        raise pytest.UsageError(
            "Integration tests need a PostgreSQL URL in one of "
            f"{', '.join(DATABASE_URL_VARIABLES)}, or settings that name a dedicated "
            "test database (TEST NAME); they never create test_<name> on a shared server."
        )

    original_options = connection.settings_dict["OPTIONS"].copy()
    schema_name = f"mahara_test_{uuid4().hex}"
    schema_created = False
    try:
        with django_db_blocker.unblock():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT namespace.nspname "
                    "FROM pg_extension AS extension "
                    "JOIN pg_namespace AS namespace ON namespace.oid = extension.extnamespace "
                    "WHERE extension.extname = %s",
                    ["vector"],
                )
                extension_row = cursor.fetchone()
                if extension_row is None:
                    raise pytest.UsageError(
                        "The PostgreSQL database configured by TEST_DATABASE_URL or "
                        "DATABASE_URL must have the vector extension installed."
                    )
                vector_schema = extension_row[0]
                cursor.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
                schema_created = True

            connection.close()
            connection.settings_dict["OPTIONS"] = {
                **original_options,
                "options": f"-c search_path={schema_name}",
            }
            MigrationRecorder(connection).ensure_schema()
            connection.close()
            connection.settings_dict["OPTIONS"] = {
                **original_options,
                "options": f"-c search_path={schema_name},{vector_schema}",
            }
            call_command("migrate", interactive=False, verbosity=0)

        yield
    finally:
        connection.close()
        connection.settings_dict["OPTIONS"] = original_options
        if schema_created:
            with django_db_blocker.unblock():
                with connection.cursor() as cursor:
                    cursor.execute(
                        sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(
                            sql.Identifier(schema_name)
                        )
                    )
            connection.close()
