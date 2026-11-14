# Placement: backend/apps/imports/services/import_launcher.py
"""Starts an admin-requested import in its own process and returns at once.

A browser scrape takes minutes, so it cannot run inside the HTTP request. It also
cannot share the Django process: sync Playwright keeps an asyncio loop running and
Django then refuses ORM calls. The launcher therefore creates the RUNNING batch,
then starts the same command a terminal or a scheduler would use:

    python -m pipelines.ingestion.offer_import --batch-id <id> --headless

The pipeline is started by module name; nothing here imports `pipelines`, so the
dependency direction (pipelines -> services) is unchanged. Output goes to
logs/imports/<batch id>.log under the repository root.
"""

import logging
from pathlib import Path
from uuid import UUID

from backend.apps.identity.models import User
from backend.apps.imports.models.records import ImportBatch
from backend.apps.imports.services import batch_processing
from backend.common import background
from backend.common.exceptions.domain import DomainError

logger = logging.getLogger(__name__)

PIPELINE_MODULE = "pipelines.ingestion.offer_import"


class ImportLaunchFailed(DomainError):
    code = "import_launch_failed"
    status_code = 503
    default_message = "The import process could not be started."


def launch_import(actor: User, source_id: UUID | str) -> ImportBatch:
    batch = batch_processing.prepare_import(actor, source_id)
    try:
        _spawn(batch.id)
    except OSError as exc:
        logger.exception("Could not start the import process for batch %s", batch.id)
        batch_processing.mark_batch_failed(batch.id)
        raise ImportLaunchFailed() from exc
    batch.refresh_from_db()
    return batch


def log_path(batch_id: UUID | str) -> Path:
    return background.logs_dir("imports") / f"{batch_id}.log"


def _spawn(batch_id: UUID) -> None:
    background.start_module(
        PIPELINE_MODULE, ["--batch-id", str(batch_id), "--headless"], log_path(batch_id)
    )
