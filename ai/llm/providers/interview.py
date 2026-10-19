import json
from typing import Any

from ai.llm.prompts.mock_interview import SYSTEM_PROMPT
from ai.llm.providers.ollama import get_chat_model

PREPARATION_SCHEMA = {
    "type": "object",
    "properties": {
        "introduction": {"type": "string"},
        "questions": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {"type": "string"},
        },
    },
    "required": ["introduction", "questions"],
    "additionalProperties": False,
}


class OllamaInterviewModel:
    def __init__(self):
        self.model = get_chat_model().bind(format="json")

    def ask(
        self, contract: str, data: Any, *, schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if schema is not None:
            contract += "\nJSON schema: " + json.dumps(schema)
        message = self.model.invoke(
            [
                ("system", SYSTEM_PROMPT + "\nJSON contract: " + contract),
                ("human", json.dumps({"untrusted_data": data}, ensure_ascii=False)),
            ],
            format=schema if schema is not None else "json",
        )
        if not isinstance(message.content, str) or len(message.content) > 40000:
            raise ValueError("Invalid model response.")
        output = json.loads(message.content)
        if not isinstance(output, dict):
            raise ValueError("Model must return an object.")
        return output

    def prepare(self, evidence: dict[str, Any]) -> dict[str, Any]:
        return self.ask(
            '{"introduction": "French greeting", "questions": ["Q1", "Q2", "Q3"]}',
            evidence,
            schema=PREPARATION_SCHEMA,
        )

    def decide(self, state: dict[str, Any]) -> dict[str, Any]:
        return self.ask(
            '{"next_action": "followup|next|evaluate", "followup": "contextual French question when requested"}',
            state,
        )

    def evaluate(self, answers: list[dict[str, Any]]) -> dict[str, Any]:
        return self.ask(
            '{"summary": "French coaching summary", "questions": [{"turn_id": "exact input ID, same order", "strengths": ["..."], "gaps": ["..."], "excerpts": ["exact nonempty substring from answer"], "improvements": ["..."]}]}',
            answers,
        )
