# Placement: tests/unit/ai/test_structured_llm.py
"""Provider fallback and the Groq strict-schema conversion."""

from typing import Any

import pytest
from pydantic import BaseModel

from ai.document_intelligence.parsing.cv_schema import EducationList
from ai.llm.providers.structured import (
    FallbackLLM,
    LLMProviderError,
    NoProviderAvailable,
    StructuredProvider,
    make_strict_schema,
)


class Answer(BaseModel):
    value: str


class Provider(StructuredProvider):
    def __init__(self, name: str, error: LLMProviderError | None = None) -> None:
        self.name = name
        self.error = error
        self.calls = 0

    def generate_structured(self, system_prompt: str, user_prompt: str, schema: Any) -> Any:
        self.calls += 1
        if self.error:
            raise self.error
        return schema(value=self.name)


def test_the_first_working_provider_answers_and_a_rate_limited_one_is_skipped() -> None:
    limited = Provider("gemini", LLMProviderError("429 quota", is_rate_limit=True))
    local = Provider("ollama")
    llm = FallbackLLM([limited, local])

    assert llm.generate_structured("s", "u", Answer).value == "ollama"
    assert llm.generate_structured("s", "u", Answer).value == "ollama"
    assert limited.calls == 1  # backed off after the rate limit
    assert llm.used == ["ollama"]


def test_a_non_rate_limit_error_is_retried_on_the_next_call() -> None:
    broken = Provider("groq", LLMProviderError("bad schema"))
    llm = FallbackLLM([broken, Provider("ollama")])
    llm.generate_structured("s", "u", Answer)
    llm.generate_structured("s", "u", Answer)
    assert broken.calls == 2


def test_all_providers_failing_raises() -> None:
    with pytest.raises(NoProviderAvailable):
        FallbackLLM([Provider("a", LLMProviderError("down"))]).generate_structured("s", "u", Answer)


def test_strict_schema_inlines_nullable_refs_and_closes_objects() -> None:
    schema = make_strict_schema(EducationList.model_json_schema())
    education = schema["$defs"]["Education"]
    assert education["additionalProperties"] is False
    assert set(education["required"]) == set(education["properties"])
    level = education["properties"]["degree_level"]
    assert "anyOf" not in level and None in level["enum"] and "null" in level["type"]
