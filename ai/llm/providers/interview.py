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

_ENTRIES = {"type": "array", "items": {"type": "string"}, "maxItems": 10}
FEEDBACK_ROW_SCHEMA = {
    "type": "object",
    "properties": {
        "strengths": _ENTRIES,
        "gaps": _ENTRIES,
        "excerpts": _ENTRIES | {"minItems": 1},
        "improvements": _ENTRIES,
    },
    "required": ["strengths", "gaps", "excerpts", "improvements"],
    "additionalProperties": False,
}
SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
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
        # One call per answer: given every answer at once, the model attached excerpts to the
        # wrong answers (2026-11-08), which breaks the grounded-excerpt rule.
        rows = [
            {"turn_id": answer["turn_id"]}
            | self.ask(
                "Write all coaching text in French. Assess this one answer to its question. "
                '"excerpts" are short passages copied word for word from the answer "text".',
                {"question": answer["question"], "text": answer["text"]},
                schema=FEEDBACK_ROW_SCHEMA,
            )
            for answer in answers
        ]
        summary = self.ask(
            "Write in French a short coaching summary of the whole mock interview, addressed "
            'directly to the candidate as "vous".',
            {"answers": [{"question": a["question"], "text": a["text"]} for a in answers]},
            schema=SUMMARY_SCHEMA,
        )
        return {"summary": summary.get("summary"), "questions": rows}
