import re
from collections.abc import Iterator
from contextlib import contextmanager

from django.db import connection
from django.db.utils import ProgrammingError

EVALUATION_SCHEMA = "eval_graphrag"
_SAFE_SCHEMA = re.compile(r"^[a-z_][a-z0-9_]*$")


def schema_options(schema_name: str, extension_schema: str | None = None) -> dict[str, object]:
    if not _SAFE_SCHEMA.fullmatch(schema_name):
        raise ValueError("Invalid PostgreSQL schema name.")
    search_path = [schema_name]
    if extension_schema and extension_schema != schema_name:
        if not _SAFE_SCHEMA.fullmatch(extension_schema):
            raise ValueError("Invalid PostgreSQL extension schema name.")
        search_path.append(extension_schema)
    return {
        **connection.settings_dict["OPTIONS"],
        "options": f"-c search_path={','.join(search_path)}",
    }


def vector_extension_schema() -> str | None:
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT namespace.nspname "
                "FROM pg_extension AS extension "
                "JOIN pg_namespace AS namespace ON namespace.oid = extension.extnamespace "
                "WHERE extension.extname = %s",
                ["vector"],
            )
            row = cursor.fetchone()
    except ProgrammingError:
        return None
    return row[0] if row else None


@contextmanager
def use_schema(schema_name: str, extension_schema: str | None = None) -> Iterator[None]:
    current_options = connection.settings_dict["OPTIONS"]
    target_options = schema_options(schema_name, extension_schema)
    if current_options == target_options:
        yield
        return
    if connection.in_atomic_block:
        raise RuntimeError("Cannot change PostgreSQL schema inside an active transaction.")

    original_options = current_options.copy()
    connection.close()
    connection.settings_dict["OPTIONS"] = target_options
    try:
        yield
    finally:
        connection.close()
        connection.settings_dict["OPTIONS"] = original_options
