# Placement: tests/integration/ai/test_ollama_cv_extraction.py
"""Opt-in: ATS analysis with section extraction on the real local Ollama (synthetic CV)."""

import os
import time

import pytest

from ai.document_intelligence.ats.analysis import analyze_cv
from ai.llm.providers.ollama import get_chat_model
from tests.fixtures.cv_review.render import render

pytestmark = [
    pytest.mark.integration,
    pytest.mark.ollama,
    pytest.mark.skipif(
        os.getenv("RUN_OLLAMA_TESTS") != "1",
        reason="Set RUN_OLLAMA_TESTS=1 to run against the real Ollama service.",
    ),
]


def test_real_model_structures_a_synthetic_cv() -> None:
    started = time.perf_counter()
    result = analyze_cv(render("de_good_pdf"), "data_engineer", "junior", model=get_chat_model())
    elapsed = time.perf_counter() - started
    print(f"analysis with extraction took {elapsed:.1f} s")

    assert result.parsed is not None
    assert result.breakdown["parse_degraded"] is False
    experience = result.parsed["sections"]["experience"]
    assert any("Example Logistics" in entry["organisation"] for entry in experience)
    assert result.breakdown["bullets"]["total"] == 8
