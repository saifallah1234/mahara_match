# Placement: pipelines/document_processing/cv_parsing.py
"""Entry point: analyse one CV in the background and store the proposal on it.

    uv run python -m pipelines.document_processing.cv_parsing --cv-id <uuid>

Started by backend/apps/candidates/services/cv_parsing.request_cv_parsing. Steps:
read the file (service) -> text (extraction/cv_text.py) -> LLM extraction
(ai/document_intelligence/parsing) -> proposal (cv_adapter.py) -> stored on the CV
(service). Django models are never imported here; only services touch the ORM.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

logger = logging.getLogger(__name__)


def run(cv_id: str, *, llm: Any = None) -> dict[str, Any]:
    """Analyse the CV and store the result. Returns the proposal. `llm` is injectable."""
    from ai.document_intelligence.parsing.cv_extractor import extract_cv
    from ai.llm.providers.structured import build_structured_llm
    from backend.apps.candidates.services import cv_parsing as service
    from pipelines.document_processing.cv_adapter import build_proposal
    from pipelines.document_processing.extraction.cv_text import read_cv

    content, mime_type = service.cv_file_for_parsing(cv_id)
    text = read_cv(content, mime_type)
    logger.info(
        "CV %s: %d characters of text, %d links, %d tables",
        cv_id,
        len(text.markdown),
        len(text.links),
        len(text.tables),
    )

    llm = llm or build_structured_llm()
    extraction = extract_cv(llm, text.markdown, links=text.links, tables=text.tables)
    extraction_data = extraction.model_dump(mode="json")
    proposal = build_proposal(extraction_data)
    provider = ", ".join(getattr(llm, "used", []) or []) or type(llm).__name__
    service.store_cv_parse_result(
        cv_id, extraction=extraction_data, proposal=proposal, provider=provider
    )
    logger.info("CV %s analysed with %s", cv_id, provider)
    return proposal


def _failure_message(exc: BaseException) -> str:
    """What the candidate sees: short, no stack trace, no provider internals."""
    from ai.llm.providers.structured import NoProviderAvailable
    from pipelines.document_processing.extraction.cv_text import EmptyCVText, UnsupportedCVFile

    if isinstance(exc, EmptyCVText | UnsupportedCVFile):
        return str(exc)
    if isinstance(exc, NoProviderAvailable):
        return "The analysis service is unavailable. Try again later."
    return "The CV could not be analysed."


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyse one CV and store a profile proposal.")
    parser.add_argument("--cv-id", required=True)
    args = parser.parse_args(argv)

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "backend.config.settings.development")
    import django

    django.setup()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    from backend.apps.candidates.services import cv_parsing as service

    try:
        run(args.cv_id)
    except BaseException as exc:
        logger.exception("CV %s could not be analysed", args.cv_id)
        service.mark_cv_parse_failed(args.cv_id, _failure_message(exc))
        print(f"CV analysis failed: {exc!r}", file=sys.stderr)
        return 1
    print("CV analysis finished.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
