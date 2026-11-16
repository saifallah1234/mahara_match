# Placement: tests/unit/ai/test_section_extraction.py
"""ATS analysis with LLM section extraction, the chat model faked (no database, no Ollama)."""

import json
from types import SimpleNamespace

import pytest

from ai.document_intelligence.ats.analysis import analyze_cv
from tests.fixtures.cv_review.fake_chat import FakeChat
from tests.fixtures.cv_review.render import render

pytestmark = pytest.mark.unit

RULE_BULLETS = 8  # de_good: 5 experience + 3 project bullets


def tampered(messages, change):
    """A faithful structure with the bullets of each entry changed."""
    entries = []
    for entry in json.loads(FakeChat().invoke(messages).content)["entries"]:
        entries.append({**entry, "bullets": change(entry["bullets"]) if entry["bullets"] else []})
    return SimpleNamespace(content=json.dumps({"entries": entries}))


def analyse(model=None, cached=None):
    return analyze_cv(render("de_good_pdf"), "data_engineer", "junior", model=model, cached=cached)


def test_scores_use_the_bullets_the_model_structured_one_section_per_call():
    model = FakeChat()
    result = analyse(model)

    assert result.breakdown["parse_degraded"] is False
    assert result.breakdown["bullets"]["total"] == RULE_BULLETS
    experience = result.parsed["sections"]["experience"]
    assert experience[0]["organisation"] == "Example Logistics"
    assert experience[0]["dates"] == "Feb 2024 - Aug 2024"
    prompts = [messages[-1][1] for messages, _ in model.calls]
    assert len(prompts) == 3  # experience, projects, education
    assert not any("Example Logistics" in p and "Open Data Loader" in p for p in prompts)
    assert all(options["format"]["required"] == ["entries"] for _, options in model.calls)


@pytest.mark.parametrize(
    "reply",
    [
        lambda messages: SimpleNamespace(content="not json"),
        lambda messages: SimpleNamespace(content=json.dumps({"entries": "none"})),
        lambda messages: SimpleNamespace(
            content=json.dumps(
                {
                    "entries": [
                        {
                            "title": "Lead",
                            "organisation": "Invented Corp",
                            "dates": "",
                            "bullets": ["Led a team of 50 engineers at Invented Corp"],
                        }
                    ]
                }
            )
        ),
        lambda messages: (_ for _ in ()).throw(ConnectionError("Ollama is down")),
        lambda messages: tampered(messages, lambda b: [x.replace("35%", "85%") for x in b]),
        lambda messages: tampered(messages, lambda b: [f"{b[0]} using Kafka", *b[1:]]),
        lambda messages: tampered(messages, lambda b: [f"{b[0]} {b[1]}", *b[2:]]),
        lambda messages: tampered(messages, lambda b: b[1:]),
    ],
    ids=[
        "invalid_json",
        "wrong_shape",
        "invented_bullet",
        "model_error",
        "changed_number",
        "added_skill",
        "merged_bullets",
        "dropped_bullet",
    ],
)
def test_bad_or_missing_model_output_falls_back_to_the_line_split(reply):
    result = analyse(FakeChat(reply))
    assert result.breakdown["parse_degraded"] is True
    assert result.breakdown["bullets"]["total"] == RULE_BULLETS
    assert result.parsed["degraded"] is True


def test_cached_structure_skips_the_model():
    first = analyse(FakeChat())
    model = FakeChat(lambda messages: pytest.fail("cached parse must not call the model"))
    again = analyse(model, cached=first.parsed)
    assert again.parsed is first.parsed
    assert again.breakdown["parse_degraded"] is False


def test_without_a_model_the_parse_is_line_based_and_degraded():
    result = analyse()
    assert result.breakdown["bullets"]["total"] == RULE_BULLETS
    assert result.breakdown["parse_degraded"] is True


def test_an_entry_the_model_repeats_is_counted_once():
    def repeat(messages):
        reply = json.loads(FakeChat().invoke(messages).content)
        untitled = {**reply["entries"][0], "title": "", "dates": ""}
        return SimpleNamespace(content=json.dumps({"entries": [untitled, *reply["entries"]]}))

    result = analyse(FakeChat(repeat))
    assert result.breakdown["parse_degraded"] is False
    assert result.breakdown["bullets"]["total"] == RULE_BULLETS
    assert len(result.parsed["sections"]["experience"]) == 1


def test_an_unreachable_model_is_called_once_not_once_per_section():
    model = FakeChat(lambda messages: (_ for _ in ()).throw(TimeoutError("Ollama hangs")))
    result = analyse(model)
    assert result.breakdown["parse_degraded"] is True
    assert len(model.calls) == 1
