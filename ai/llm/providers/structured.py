# Placement: ai/llm/providers/structured.py
"""Structured-output LLM calls with provider fallback (Gemini -> Groq -> local Ollama).

Ported from the OneTech agent project. One entry point, generate_structured(system,
user, schema), returns a validated Pydantic object. Providers are tried in order;
a rate-limited or overloaded provider is skipped for a minute.

Privacy (decision 2026-11-14): with GEMINI_API_KEY / GROQ_API_KEY set, the prompt
(for CV extraction: the CV text) is sent to Google / Groq. Without keys only the
local Ollama model is used and nothing leaves the machine.

Environment: GEMINI_API_KEY, GEMINI_MODEL (gemini-3.5-flash), GROQ_API_KEY,
GROQ_MODEL (openai/gpt-oss-120b), CV_OLLAMA_MODEL or OLLAMA_MODEL (qwen2.5:7b),
OLLAMA_BASE_URL, LLM_TIMEOUT_SECONDS (120 for remote providers).
"""

from __future__ import annotations

import copy
import json
import logging
import os
import time
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

logger = logging.getLogger(__name__)

SchemaT = TypeVar("SchemaT", bound=BaseModel)

_RATE_LIMIT_TOKENS = (
    "429",
    "resource_exhausted",
    "quota",
    "rate limit",
    "503",
    "unavailable",
    "overloaded",
    "high demand",
)


class LLMProviderError(Exception):
    def __init__(self, message: str, *, is_rate_limit: bool = False) -> None:
        super().__init__(message)
        self.is_rate_limit = is_rate_limit


class NoProviderAvailable(RuntimeError):
    """Every provider failed or was skipped."""


class StructuredProvider(ABC):
    name: str

    @abstractmethod
    def generate_structured(
        self, system_prompt: str, user_prompt: str, schema: type[SchemaT]
    ) -> SchemaT: ...

    @staticmethod
    def _error(exc: Exception) -> LLMProviderError:
        message = str(exc)
        lowered = message.lower()
        return LLMProviderError(
            message, is_rate_limit=any(token in lowered for token in _RATE_LIMIT_TOKENS)
        )


class GeminiProvider(StructuredProvider):
    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        self._client = genai.Client(
            api_key=api_key, http_options=types.HttpOptions(timeout=timeout_seconds * 1000)
        )
        self.model = model
        self.name = f"gemini:{model}"

    def generate_structured(
        self, system_prompt: str, user_prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config=self._types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0,
                ),
            )
            return schema.model_validate(json.loads(response.text or "{}"))
        except Exception as exc:
            raise self._error(exc) from exc


class GroqProvider(StructuredProvider):
    def __init__(self, api_key: str, model: str, timeout_seconds: int) -> None:
        from groq import Groq

        self._client = Groq(api_key=api_key, timeout=timeout_seconds)
        self.model = model
        self.name = f"groq:{model}"

    def generate_structured(
        self, system_prompt: str, user_prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": schema.__name__,
                        "strict": True,
                        "schema": make_strict_schema(schema.model_json_schema()),
                    },
                },
            )
            return schema.model_validate(json.loads(response.choices[0].message.content or "{}"))
        except Exception as exc:
            raise self._error(exc) from exc


class OllamaProvider(StructuredProvider):
    """Local model; slow on CPU (about 80 s per call with qwen2.5:7b) but private."""

    def __init__(self, model: str, base_url: str) -> None:
        from langchain_ollama import ChatOllama

        self._chat = ChatOllama(model=model, base_url=base_url, temperature=0)
        self.model = model
        self.name = f"ollama:{model}"

    def generate_structured(
        self, system_prompt: str, user_prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        try:
            result = self._chat.with_structured_output(schema).invoke(
                [("system", system_prompt), ("human", user_prompt)]
            )
            return schema.model_validate(result)
        except Exception as exc:
            raise self._error(exc) from exc


class FallbackLLM:
    """Tries each provider in order; a rate-limited one is skipped for BACKOFF_SECONDS."""

    BACKOFF_SECONDS = 60

    def __init__(self, providers: list[StructuredProvider]) -> None:
        if not providers:
            raise NoProviderAvailable("No LLM provider is configured.")
        self._providers = [{"provider": p, "blocked_until": 0.0} for p in providers]
        self.used: list[str] = []  # providers that answered, in call order (for traceability)

    @property
    def names(self) -> list[str]:
        return [entry["provider"].name for entry in self._providers]  # type: ignore[attr-defined]

    def generate_structured(
        self, system_prompt: str, user_prompt: str, schema: type[SchemaT]
    ) -> SchemaT:
        last_error: Exception | None = None
        for entry in self._providers:
            provider: StructuredProvider = entry["provider"]  # type: ignore[assignment]
            if time.time() < float(entry["blocked_until"]):  # type: ignore[arg-type]
                continue
            try:
                result = provider.generate_structured(system_prompt, user_prompt, schema)
                if provider.name not in self.used:
                    self.used.append(provider.name)
                return result
            except LLMProviderError as exc:
                last_error = exc
                if exc.is_rate_limit:
                    entry["blocked_until"] = time.time() + self.BACKOFF_SECONDS
                logger.warning("%s failed (%s), trying the next provider", provider.name, exc)
        raise NoProviderAvailable(f"All LLM providers failed. Last error: {last_error}")


def build_structured_llm() -> FallbackLLM:
    """Gemini and Groq when their keys are set, then the local Ollama model."""
    timeout = int(os.getenv("LLM_TIMEOUT_SECONDS", "120"))
    providers: list[StructuredProvider] = []
    if gemini_key := os.getenv("GEMINI_API_KEY"):
        providers.append(
            GeminiProvider(gemini_key, os.getenv("GEMINI_MODEL", "gemini-3.5-flash"), timeout)
        )
    if groq_key := os.getenv("GROQ_API_KEY"):
        providers.append(
            GroqProvider(groq_key, os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"), timeout)
        )
    providers.append(
        OllamaProvider(
            os.getenv("CV_OLLAMA_MODEL") or os.getenv("OLLAMA_MODEL") or "qwen2.5:7b",
            os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )
    )
    return FallbackLLM(providers)


# -- Groq / OpenAI strict json_schema -----------------------------------------


def make_strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Pydantic JSON schema -> the subset strict json_schema mode accepts.

    Every object gets additionalProperties=false and all properties required, and
    `X | None` (anyOf [$ref X, null]) is inlined as X with "null" added to its type.
    """
    schema = copy.deepcopy(schema)
    definitions = schema.get("$defs", {})
    _collapse_nullable_refs(schema, definitions)
    _enforce_strict_objects(schema)
    return schema


def _collapse_nullable_refs(node: Any, definitions: dict[str, Any]) -> None:
    if isinstance(node, dict):
        branches = node.get("anyOf")
        if isinstance(branches, list):
            non_null = [b for b in branches if b.get("type") != "null"]
            if len(non_null) == 1 and len(non_null) < len(branches):
                target = non_null[0]
                if "$ref" in target:
                    target = definitions[target["$ref"].rsplit("/", 1)[-1]]
                del node["anyOf"]
                node.update(copy.deepcopy(target))
                kind = node.get("type")
                if isinstance(kind, list):
                    if "null" not in kind:
                        kind.append("null")
                elif isinstance(kind, str):
                    node["type"] = [kind, "null"]
                else:
                    node["type"] = "null"
                if "enum" in node and None not in node["enum"]:
                    node["enum"] = [*node["enum"], None]
        for value in node.values():
            _collapse_nullable_refs(value, definitions)
    elif isinstance(node, list):
        for item in node:
            _collapse_nullable_refs(item, definitions)


def _enforce_strict_objects(node: Any) -> None:
    if isinstance(node, dict):
        kind = node.get("type")
        if kind == "object" or (isinstance(kind, list) and "object" in kind):
            node["additionalProperties"] = False
            if "properties" in node:
                node["required"] = list(node["properties"])
        for value in node.values():
            _enforce_strict_objects(value)
    elif isinstance(node, list):
        for item in node:
            _enforce_strict_objects(item)
