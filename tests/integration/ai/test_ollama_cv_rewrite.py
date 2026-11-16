# Placement: tests/integration/ai/test_ollama_cv_rewrite.py
"""Opt-in: bullet rewrites on the real local Ollama, printing the validator rejection rate."""

import os

import pytest

from ai.document_intelligence.ats.profiles import roles
from ai.document_intelligence.ats.rewrite import MAX_BULLET_WORDS, rejection_reason, rewrite_bullet
from ai.llm.providers.embeddings import embed
from ai.llm.providers.ollama import get_chat_model
from tests.unit.ai.test_cv_rewrite import FIXED

pytestmark = [
    pytest.mark.integration,
    pytest.mark.ollama,
    pytest.mark.skipif(
        os.getenv("RUN_OLLAMA_TESTS") != "1",
        reason="Set RUN_OLLAMA_TESTS=1 to run against the real Ollama service.",
    ),
]


def test_real_model_rewrites_are_validated_or_fall_back() -> None:
    role, model = roles()["data_engineer"], get_chat_model(timeout=30)
    originals = sorted({original for original, _ in FIXED})
    results = [rewrite_bullet(original, role, model, embed=embed) for original in originals]
    for result in results:
        print(f"{result['original']!r} -> {result['text'] or result['suggestion']!r}")
        if result["source"] == "model":
            assert (
                rejection_reason(result["original"], result["text"], role, MAX_BULLET_WORDS) is None
            )
    rejected = sum(result["source"] == "rule" for result in results)
    print(f"fallback rate on the real model: {rejected}/{len(results)}")
