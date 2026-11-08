import json
import re
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

# Without a schema the model returned a "followup: " key and copied the placeholder text (2026-11-08).
DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "next_action": {"type": "string", "enum": ["followup", "next", "evaluate"]},
        "followup": {"type": "string"},
    },
    "required": ["next_action", "followup"],
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
        output = self.ask(
            '{"next_action": "followup" | "next" | "evaluate", "followup": string}. Choose "followup" '
            'only when the latest answer is vague or incomplete; then write in "followup" one short '
            "question in French, addressed to the candidate, about that answer. Otherwise leave "
            '"followup" empty.',
            state,
            schema=DECISION_SCHEMA,
        )
        # The model copies the main questions' "Q1:" numbering into the follow-up.
        if isinstance(output.get("followup"), str):
            output["followup"] = re.sub(r"^\s*Q\d+\s*[:.)-]\s*", "", output["followup"])
        return output

    def evaluate(self, answers: list[dict[str, Any]]) -> dict[str, Any]:
        return self.ask(
            '{"summary": "French coaching summary", "questions": [{"turn_id": "exact input ID, same order", "strengths": ["..."], "gaps": ["..."], "excerpts": ["exact nonempty substring from answer"], "improvements": ["..."]}]}',
            answers,
        )
